import pytest
from pydantic import ValidationError

from app.agents.contracts import (
    AgentResult,
    ClaimReview,
    CriticReport,
    Evidence,
    ScoutOutput,
)


def test_agent_result_requires_reason_on_failure() -> None:
    with pytest.raises(ValidationError, match="reason is required"):
        AgentResult[ScoutOutput](agent="scout", status="unavailable", confidence=0.0)


def test_agent_result_ok_without_reason() -> None:
    result = AgentResult[ScoutOutput](
        agent="scout",
        status="ok",
        data=ScoutOutput(matches=[], total_candidates=0, deduped=0),
        confidence=0.9,
    )
    assert result.data is not None
    assert result.data.total_candidates == 0


def test_evidence_excerpt_truncated_to_200_chars() -> None:
    evidence = Evidence(source_type="review", excerpt="x" * 500)
    assert evidence.excerpt is not None
    assert len(evidence.excerpt) == 200
    assert evidence.excerpt.endswith("...")


def test_critic_report_counts_validated() -> None:
    reviews = [
        ClaimReview(claim="a", agent="price", action="approved"),
        ClaimReview(claim="b", agent="review", action="rejected", reason="no source"),
    ]
    with pytest.raises(ValidationError, match="counts do not match"):
        CriticReport(reviews=reviews, approved=2, downgraded=0, rejected=0)
    report = CriticReport(reviews=reviews, approved=1, downgraded=0, rejected=1)
    assert report.rejected == 1
