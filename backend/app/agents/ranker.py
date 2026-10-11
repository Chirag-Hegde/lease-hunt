"""Ranker: blends per-dimension scores into a final ranking. The formula is
exposed to the UI; re-ranking on weight change happens client-side with the
same formula."""

from typing import Any

from app.agents.contracts import (
    DimensionScores,
    RankedListing,
    RankWeights,
    ScoutOutput,
)

FORMULA = (
    "final = Σ(weight_d × score_d) / Σ(weight_d) over available dimensions "
    "(match, commute, value, reputation, lease_risk); scores are 0–100"
)


def _get_data(results: dict[str, Any], agent: str) -> dict[str, Any] | None:
    envelope = results.get(agent)
    if not envelope or envelope.get("status") not in ("ok", "partial"):
        return None
    data: dict[str, Any] | None = envelope.get("data")
    return data


def dimension_scores(match_score: float, results: dict[str, Any]) -> DimensionScores:
    scores = DimensionScores(match=match_score)

    commute = _get_data(results, "commute")
    if commute is not None:
        scores.commute = float(commute["overall_score"])

    price = _get_data(results, "price")
    if price is not None:
        # Cheaper than comps → better value. percentile 50 ≈ fair → 50.
        scores.value = round(100.0 - float(price["percentile"]), 1)

    review = _get_data(results, "review")
    if review is not None:
        scores.reputation = float(review["management_score"])

    lease = _get_data(results, "lease")
    if lease is not None:
        scores.lease_risk = round(100.0 - float(lease["risk_score"]), 1)

    return scores


def final_score(scores: DimensionScores, weights: RankWeights) -> float:
    pairs: list[tuple[float, float]] = []
    for dim in ("match", "commute", "value", "reputation", "lease_risk"):
        value = getattr(scores, dim)
        weight = getattr(weights, dim)
        if value is not None and weight > 0:
            pairs.append((weight, value))
    if not pairs:
        return 0.0
    return round(sum(w * v for w, v in pairs) / sum(w for w, _ in pairs), 1)


def _top_pros(match_explanation: str, scores: DimensionScores) -> list[str]:
    pros: list[str] = []
    if scores.commute is not None and scores.commute >= 70:
        pros.append("Great commute to your places")
    if scores.value is not None and scores.value >= 60:
        pros.append("Priced below comparable units")
    if scores.reputation is not None and scores.reputation >= 70:
        pros.append("Well-reviewed building")
    for part in match_explanation.split("; "):
        if part.startswith(("has ", "bonus: ")) and len(pros) < 3:
            pros.append(part[0].upper() + part[1:])
    return pros[:3]


def _top_red_flag(results: dict[str, Any]) -> str | None:
    review = _get_data(results, "review")
    if review and review.get("red_flags"):
        return str(review["red_flags"][0])
    lease = _get_data(results, "lease")
    if lease:
        highs = [f for f in lease.get("findings", []) if f.get("severity") == "high"]
        if highs:
            return f"Lease: {highs[0]['explanation']}"
    price = _get_data(results, "price")
    if price and float(price.get("percentile", 0)) >= 80:
        return "Priced well above comparable units"
    return None


def rank_listings(
    scout: ScoutOutput,
    listing_results: dict[str, dict[str, Any]],
    weights: RankWeights,
    critic_verified_ids: set[str] | None = None,
) -> list[RankedListing]:
    ranked: list[RankedListing] = []
    for match in scout.matches:
        results = listing_results.get(match.listing.id, {})
        scores = dimension_scores(match.match_score, results)
        ranked.append(
            RankedListing(
                listing_id=match.listing.id,
                scores=scores,
                final_score=final_score(scores, weights),
                top_pros=_top_pros(match.explanation, scores),
                top_red_flag=_top_red_flag(results),
                critic_verified=bool(
                    critic_verified_ids and match.listing.id in critic_verified_ids
                ),
            )
        )
    ranked.sort(key=lambda r: r.final_score, reverse=True)
    return ranked
