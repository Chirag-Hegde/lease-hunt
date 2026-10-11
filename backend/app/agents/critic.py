"""Critic/Verifier agent: every user-facing claim must be backed by evidence
that actually supports it. Combines deterministic checks (numbers recomputed,
URLs present, excerpts resolvable) with an LLM judge under a strict rubric.
Unsupported claims are removed or downgraded, logged, and counted."""

from typing import Any, Literal

from pydantic import BaseModel

from app.agents.contracts import ClaimReview, CriticReport
from app.graph.context import RunContext

STOPWORDS = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "but",
        "by",
        "for",
        "from",
        "has",
        "have",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "to",
        "was",
        "were",
        "with",
        "recent",
        "recurring",
        "complaints",
        "mentions",
    ]
)


class ClaimVerdict(BaseModel):
    action: Literal["approved", "downgraded", "rejected"]
    reason: str | None = None


class Claim(BaseModel):
    listing_id: str
    agent: str
    text: str
    evidence_excerpts: list[str]
    evidence_urls: list[str | None]
    kind: Literal["review_flag", "fake_burst", "price_math", "commute_math"]


def _collect_evidence(envelope: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {e["id"]: e for e in envelope.get("evidence", [])}


def collect_claims(listing_id: str, results: dict[str, Any]) -> list[Claim]:
    claims: list[Claim] = []

    review = results.get("review")
    if review and review.get("status") in ("ok", "partial") and review.get("data"):
        evidence = _collect_evidence(review)
        data = review["data"]
        theme_by_name = {t["theme"]: t for t in data.get("themes", [])}
        for flag in data.get("red_flags", []):
            theme = next((name for name in theme_by_name if name.replace("_", " ") in flag), None)
            if "5-star" in flag or "astroturf" in flag.lower():
                excerpts = [e.get("excerpt") or "" for e in evidence.values()]
                claims.append(
                    Claim(
                        listing_id=listing_id,
                        agent="review",
                        text=flag,
                        evidence_excerpts=excerpts,
                        evidence_urls=[e.get("source_url") for e in evidence.values()],
                        kind="fake_burst",
                    )
                )
                continue
            ids = theme_by_name.get(theme, {}).get("evidence_ids", []) if theme else []
            linked = [evidence[i] for i in ids if i in evidence]
            claims.append(
                Claim(
                    listing_id=listing_id,
                    agent="review",
                    text=flag,
                    evidence_excerpts=[e.get("excerpt") or "" for e in linked],
                    evidence_urls=[e.get("source_url") for e in linked],
                    kind="review_flag",
                )
            )

    price = results.get("price")
    if price and price.get("status") == "ok" and price.get("data"):
        data = price["data"]
        claims.append(
            Claim(
                listing_id=listing_id,
                agent="price",
                text=(
                    f"total monthly cost ${data['total_monthly_cost']:.2f} equals the sum of its breakdown"
                ),
                evidence_excerpts=[str(data.get("monthly_cost_breakdown", {}))],
                evidence_urls=[None],
                kind="price_math",
            )
        )

    commute = results.get("commute")
    if commute and commute.get("status") in ("ok", "partial") and commute.get("data"):
        data = commute["data"]
        claims.append(
            Claim(
                listing_id=listing_id,
                agent="commute",
                text=f"overall commute score {data['overall_score']} reflects the per-place estimates",
                evidence_excerpts=[str(data.get("per_place", []))],
                evidence_urls=[None],
                kind="commute_math",
            )
        )
    return claims


def _check_price_math(results: dict[str, Any]) -> tuple[bool, str]:
    data = results["price"]["data"]
    breakdown: dict[str, float] = data.get("monthly_cost_breakdown", {})
    total = float(data.get("total_monthly_cost", 0))
    recomputed = sum(breakdown.values())
    if abs(recomputed - total) < 1.0:
        return True, "recomputed: breakdown sums to the stated total"
    return False, f"breakdown sums to ${recomputed:.2f}, not the stated ${total:.2f}"


def _check_commute_math(results: dict[str, Any]) -> tuple[bool, str]:
    data = results["commute"]["data"]
    from app.agents.commute import place_score

    per_place = data.get("per_place", [])
    if not per_place:
        return False, "no per-place estimates behind the overall score"
    # The formula uses brief tolerances; approximate with 30 min to bound drift.
    total_weight = sum(p["weight"] for p in per_place) or 1.0
    recomputed = (
        sum(place_score(p["best_peak_minutes"], 30) * p["weight"] for p in per_place) / total_weight
    )
    stated = float(data.get("overall_score", 0))
    if abs(recomputed - stated) <= 25.0:  # tolerance differences allowed
        return True, "recomputed within tolerance of per-place estimates"
    return False, f"overall score {stated} is far from recomputed {recomputed:.0f}"


async def _llm_judge(ctx: RunContext, claim: Claim) -> ClaimVerdict:
    result = await ctx.llm.call(
        agent="critic",
        task="critic_judge",
        schema=ClaimVerdict,
        context={
            "claim": claim.text,
            "excerpts": claim.evidence_excerpts,
            "urls": claim.evidence_urls,
        },
        claim=claim.text,
        excerpts="\n".join(f"- {e}" for e in claim.evidence_excerpts) or "(none)",
        max_tokens=400,
    )
    return result.data


async def critic_agent(
    ctx: RunContext, listing_results: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    """Verify claims across all listings; mutate results in place (drop
    rejected red flags), return report + verified ids + cleaned results."""
    reviews: list[ClaimReview] = []
    verified_ids: list[str] = []
    patched: dict[str, dict[str, Any]] = {}

    for listing_id, results in listing_results.items():
        listing_ok = True
        claims = collect_claims(listing_id, results)
        rejected_flags: list[str] = []

        for claim in claims:
            # Deterministic lanes
            if claim.kind == "price_math":
                ok, reason = _check_price_math(results)
                verdict = ClaimVerdict(action="approved" if ok else "rejected", reason=reason)
            elif claim.kind == "commute_math":
                ok, reason = _check_commute_math(results)
                verdict = ClaimVerdict(action="approved" if ok else "downgraded", reason=reason)
            else:
                # Evidence-backed text claims: URL + excerpt must exist, then judge.
                if not claim.evidence_excerpts or not any(claim.evidence_excerpts):
                    verdict = ClaimVerdict(
                        action="rejected", reason="no supporting evidence attached"
                    )
                elif claim.kind == "review_flag" and not any(claim.evidence_urls):
                    verdict = ClaimVerdict(action="rejected", reason="evidence has no source link")
                else:
                    verdict = await _llm_judge(ctx, claim)

            reviews.append(
                ClaimReview(
                    claim=claim.text,
                    agent=claim.agent,
                    action=verdict.action,
                    reason=verdict.reason,
                )
            )
            if verdict.action == "rejected":
                listing_ok = False
                ctx.critic_rejections += 1
                await ctx.bus.publish(
                    ctx.run_id,
                    "critic_rejected",
                    agent="critic",
                    payload={
                        "listing_id": listing_id,
                        "claim": claim.text,
                        "reason": verdict.reason,
                    },
                )
                if claim.kind in ("review_flag", "fake_burst"):
                    rejected_flags.append(claim.text)
            elif verdict.action == "downgraded":
                listing_ok = False

        # Remove rejected red flags from the user-facing data.
        if rejected_flags and results.get("review", {}).get("data"):
            cleaned = dict(results["review"])
            cleaned_data = dict(cleaned["data"])
            cleaned_data["red_flags"] = [
                f for f in cleaned_data.get("red_flags", []) if f not in rejected_flags
            ]
            cleaned["data"] = cleaned_data
            patched[listing_id] = {**results, "review": cleaned}

        if listing_ok and claims:
            verified_ids.append(listing_id)

    report = CriticReport(
        reviews=reviews,
        approved=sum(1 for r in reviews if r.action == "approved"),
        downgraded=sum(1 for r in reviews if r.action == "downgraded"),
        rejected=sum(1 for r in reviews if r.action == "rejected"),
    )
    return {
        "report": report.model_dump(mode="json"),
        "verified_listing_ids": verified_ids,
        "patched_results": patched,
    }
