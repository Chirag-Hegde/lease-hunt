"""Lease pipeline tests against the generated ground-truth leases."""

from pathlib import Path

from httpx import AsyncClient

from app.api.routes_leases import wait_for_lease
from app.seed.leases import generate_leases
from app.services.pdf import parse_lease_pdf


def _ensure_leases() -> list[dict[str, object]]:
    return generate_leases()


def test_pdf_parse_segments_with_coordinates() -> None:
    manifest = _ensure_leases()
    pdf = Path(__file__).parents[2] / "seed" / "generated" / "leases" / manifest[0]["file"]  # type: ignore[index]
    parsed = parse_lease_pdf(str(pdf))
    assert parsed.page_count >= 1
    assert not parsed.ocr_used
    headed = [s for s in parsed.segments if s.heading]
    assert len(headed) >= 10  # every numbered clause found
    for segment in parsed.segments:
        x0, y0, x1, y1 = segment.bbox
        assert x1 > x0 and y1 > y0
        assert segment.page >= 1


async def _analyze_sample(client: AsyncClient, key: str) -> dict[str, object]:
    _ensure_leases()
    resp = await client.post(f"/api/leases/samples/{key}")
    assert resp.status_code == 200, resp.text
    lease_id = resp.json()["id"]
    await wait_for_lease(lease_id)
    resp = await client.get(f"/api/leases/{lease_id}")
    body: dict[str, object] = resp.json()
    return body


async def test_clean_lease_scores_low(client: AsyncClient) -> None:
    body = await _analyze_sample(client, "lease_1_cedar_grove_clean")
    assert body["status"] == "finished", body.get("error")
    assert isinstance(body["risk_score"], int)
    assert body["risk_score"] <= 20
    analysis = body["analysis"]
    assert isinstance(analysis, dict)
    highs = [f for f in analysis["findings"] if f["severity"] == "high"]  # type: ignore[index]
    assert highs == []


async def test_kitchen_sink_lease_scores_high(client: AsyncClient) -> None:
    body = await _analyze_sample(client, "lease_6_el_camino_kitchen_sink")
    assert body["status"] == "finished", body.get("error")
    assert isinstance(body["risk_score"], int)
    assert body["risk_score"] >= 80
    analysis = body["analysis"]
    assert isinstance(analysis, dict)
    findings = analysis["findings"]  # type: ignore[index]
    assert isinstance(findings, list)

    by_type = {f["clause_type"]: f for f in findings}
    # The dangerous clauses are detected with high severity + verified citations.
    for expected in ("security_deposit", "liability_waiver", "arbitration", "as_is"):
        assert expected in by_type, f"missing {expected}"
        assert by_type[expected]["severity"] == "high"

    waiver = by_type["liability_waiver"]
    assert waiver["citation"]["page"] >= 1
    assert "negligence" in waiver["citation"]["quote"].lower()
    note = waiver["jurisdiction_note"]
    assert note["verified"] is True
    assert "1953" in note["text"]
    assert note["source_url"] and "leginfo" in note["source_url"]

    # Findings are sorted by severity, high first.
    severities = [f["severity"] for f in findings]
    assert severities.index("high") == 0

    summary = body["summary"]
    assert isinstance(summary, dict)
    assert summary["counts"]["high"] >= 7
    assert len(summary["questions_for_landlord"]) >= 5

    # Disclaimer always present on the contract.
    assert "Not legal advice" in analysis["disclaimer"]  # type: ignore[index]


async def test_unverified_rules_marked(client: AsyncClient) -> None:
    body = await _analyze_sample(client, "lease_3_marlow_commons_fees")
    analysis = body["analysis"]
    assert isinstance(analysis, dict)
    findings = analysis["findings"]  # type: ignore[index]
    guest = next(f for f in findings if f["clause_type"] == "guest_limits")
    assert guest["jurisdiction_note"]["verified"] is False


async def test_upload_validation(client: AsyncClient) -> None:
    resp = await client.post(
        "/api/leases",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 415
    resp = await client.post(
        "/api/leases",
        files={"file": ("fake.pdf", b"not a pdf", "application/pdf")},
    )
    assert resp.status_code == 415
