"""Review agent: fetch building reviews/posts, embed + cluster, label themes
with the LLM (fixed taxonomy), detect recency trends and fake-review bursts."""

import re
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field

from app.agents.contracts import (
    AgentResult,
    Evidence,
    ListingModel,
    ReviewInsights,
    ReviewTheme,
    ThemeInsight,
)
from app.db.session import get_session_factory
from app.graph.context import RunContext
from app.providers.llm.embeddings import cosine_similarity, get_embedding_provider
from app.providers.reviews.base import ReviewDoc

RECENT_WINDOW_DAYS = 180
CLUSTER_SIMILARITY = 0.55
FAKE_BURST_MIN = 4
FAKE_BURST_WINDOW_DAYS = 14


class ClusterLabel(BaseModel):
    """LLM output for one review cluster."""

    theme: ReviewTheme
    sentiment: float = Field(ge=-1.0, le=1.0)


def slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def cluster_reviews(docs: list[ReviewDoc], embeddings: list[list[float]]) -> list[list[int]]:
    """Greedy cosine-threshold clustering — small n, deterministic order."""
    clusters: list[list[int]] = []
    centroids: list[list[float]] = []
    for i, vector in enumerate(embeddings):
        best, best_sim = -1, CLUSTER_SIMILARITY
        for ci, centroid in enumerate(centroids):
            sim = cosine_similarity(vector, centroid)
            if sim > best_sim:
                best, best_sim = ci, sim
        if best >= 0:
            clusters[best].append(i)
            members = clusters[best]
            centroids[best] = [
                sum(embeddings[m][d] for m in members) / len(members) for d in range(len(vector))
            ]
        else:
            clusters.append([i])
            centroids.append(list(vector))
    return clusters


def _as_utc(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt


def detect_fake_burst(docs: list[ReviewDoc]) -> tuple[bool, str | None]:
    """Flag a burst of ≥4 near-5-star reviews inside a 14-day window."""
    rated = sorted(
        (
            (_as_utc(d.posted_at), d.rating)
            for d in docs
            if d.rating and d.rating >= 4.5 and d.posted_at
        ),
        key=lambda x: x[0] or datetime.min.replace(tzinfo=UTC),
    )
    if len(rated) < FAKE_BURST_MIN:
        return False, None
    window = timedelta(days=FAKE_BURST_WINDOW_DAYS)
    for i in range(len(rated) - FAKE_BURST_MIN + 1):
        start = rated[i][0]
        end = rated[i + FAKE_BURST_MIN - 1][0]
        if start and end and (end - start) <= window:
            return True, (
                f"{FAKE_BURST_MIN}+ five-star reviews posted within "
                f"{FAKE_BURST_WINDOW_DAYS} days of each other — possible astroturfing; "
                "weigh recent praise accordingly."
            )
    return False, None


def trend_for(members: list[ReviewDoc]) -> tuple[str, bool]:
    now = datetime.now(UTC)
    recent = sum(
        1 for d in members if (dt := _as_utc(d.posted_at)) and (now - dt).days <= RECENT_WINDOW_DAYS
    )
    older = len(members) - recent
    if recent >= 2 and recent > older:
        return "worsening", True
    if older > 0 and recent == 0:
        return "improving", False
    return "stable", False


async def review_agent(ctx: RunContext, listing: ListingModel) -> AgentResult[ReviewInsights]:
    if not listing.building_name:
        return AgentResult[ReviewInsights](
            agent="review",
            status="unavailable",
            reason="small/private listing with no identifiable building — no public review trail",
            confidence=0.0,
        )

    building_key = slugify(listing.building_name)
    docs: list[ReviewDoc] = []
    async with get_session_factory()() as session:
        for provider in ctx.reviews:
            await ctx.bus.publish(
                ctx.run_id,
                "tool_called",
                agent="review",
                payload={
                    "tool": "fetch_reviews",
                    "provider": provider.name,
                    "building": building_key,
                },
            )
            try:
                docs.extend(await provider.fetch(building_key, listing.building_name, session))
            except Exception:
                continue

    if not docs:
        return AgentResult[ReviewInsights](
            agent="review",
            status="unavailable",
            reason=f"no reviews or posts found for {listing.building_name}",
            confidence=0.0,
        )

    # Embed + cluster, then label each cluster once (cheap-model task).
    embedder = get_embedding_provider()
    vectors = await embedder.embed([d.text for d in docs])
    clusters = cluster_reviews(docs, vectors)

    theme_members: dict[ReviewTheme, list[ReviewDoc]] = {}
    theme_evidence: dict[ReviewTheme, list[Evidence]] = {}
    theme_sentiment: dict[ReviewTheme, list[float]] = {}
    positive_count = 0

    for cluster in clusters:
        members = [docs[i] for i in cluster]
        texts = [m.text[:400] for m in members[:6]]
        result = await ctx.llm.call(
            agent="review",
            task="review_theme_label",
            schema=ClusterLabel,
            context={"texts": texts, "ratings": [m.rating for m in members]},
            texts="\n---\n".join(texts),
        )
        label = result.data
        if label.sentiment > 0.25:
            positive_count += len(members)
            continue  # positive clusters inform the score but aren't complaints
        theme_members.setdefault(label.theme, []).extend(members)
        theme_sentiment.setdefault(label.theme, []).append(label.sentiment)
        for member in members[:2]:
            theme_evidence.setdefault(label.theme, []).append(
                Evidence(
                    source_type="reddit" if member.source_type == "reddit" else "review",
                    source_url=member.url,
                    excerpt=member.text[:200],
                    retrieved_at=datetime.now(UTC),
                )
            )

    themes: list[ThemeInsight] = []
    red_flags: list[str] = []
    for theme, members in sorted(theme_members.items(), key=lambda kv: -len(kv[1])):
        sentiments = theme_sentiment.get(theme, [-0.4])
        avg_sentiment = sum(sentiments) / len(sentiments)
        trend, spike = trend_for(members)
        evidence_ids = [e.id for e in theme_evidence.get(theme, [])]
        themes.append(
            ThemeInsight(
                theme=theme,
                frequency=len(members),
                sentiment=round(avg_sentiment, 2),
                trend=trend,
                recent_spike=spike,
                evidence_ids=evidence_ids,
            )
        )
        if len(members) >= 2 and avg_sentiment < -0.2:
            flag = f"Recurring {theme.replace('_', ' ')} complaints ({len(members)} mentions"
            flag += ", spiking recently)" if spike else ")"
            red_flags.append(flag)

    fake, fake_note = detect_fake_burst(docs)
    if fake:
        red_flags.append("Suspicious burst of 5-star reviews")

    spike_themes = [t for t in themes if t.recent_spike]
    if spike_themes and any(t.theme == "management" for t in spike_themes):
        red_flags.append("Complaints spiked in the last 6 months — possibly new management")

    # Management score: positive share up, complaint mass and spikes down.
    complaint_mass = sum(t.frequency * (0.5 - t.sentiment / 2) for t in themes)
    score = 72.0 + 4.0 * positive_count - 9.0 * complaint_mass - (8.0 if fake else 0.0)
    score -= 6.0 * sum(1 for t in themes if t.recent_spike)
    score = max(5.0, min(score, 98.0))

    data = ReviewInsights(
        building_key=building_key,
        review_count=len(docs),
        themes=themes,
        management_score=round(score, 1),
        red_flags=red_flags[:4],
        fake_review_suspicion=fake,
        fake_review_note=fake_note,
    )
    all_evidence = [e for items in theme_evidence.values() for e in items]
    if fake and docs:
        burst_doc = next((d for d in docs if d.rating and d.rating >= 4.5), docs[0])
        all_evidence.append(
            Evidence(
                source_type="review",
                source_url=burst_doc.url,
                excerpt=burst_doc.text[:200],
            )
        )
    return AgentResult[ReviewInsights](
        agent="review",
        status="ok",
        data=data,
        evidence=all_evidence[:20],
        confidence=min(0.4 + 0.06 * len(docs), 0.9),
    )
