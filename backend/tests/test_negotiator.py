from httpx import AsyncClient

from app.agents.contracts import Evidence, Fee, PriceAnalysis
from app.agents.negotiator import LeverageContext, build_leverage_points, draft_negotiations
from app.api.routes_leases import wait_for_lease
from app.seed.leases import generate_leases
from app.seed.load import seed
from app.services.llm import LLMService
from tests.test_agents import _listing
from tests.test_orchestration import _create_brief_and_run, _run_to_completion


def _price() -> tuple[PriceAnalysis, list[Evidence]]:
    price = PriceAnalysis(
        comp_ids=["c1", "c2", "c3"],
        comp_count=8,
        percentile=78.0,
        fair_range_low=2900,
        fair_range_high=3050,
        total_monthly_cost=3420.0,
        monthly_cost_breakdown={"rent": 3200.0, "estimated utilities": 120.0, "parking": 100.0},
        method="test",
    )
    evidence = [Evidence(source_type="computed", excerpt="8 comps, fair range $2,900–$3,050")]
    return price, evidence


def test_leverage_points_all_cite_evidence() -> None:
    price, evidence = _price()
    listing = _listing(
        rent=3200,
        fees=[
            Fee(name="admin fee", amount=300, period="one_time", mandatory=True),
            Fee(name="parking", amount=100, period="monthly", mandatory=False),
        ],
    )
    ctx = LeverageContext(listing=listing, price=price, price_evidence=evidence)
    points, asks = build_leverage_points(ctx)
    assert len(points) >= 2
    assert all(p.evidence_ids for p in points)  # contract also enforces this
    kinds = {a.kind for a in asks}
    assert {"rent_reduction", "waived_fee", "free_parking"} <= kinds
    reduction = next(a for a in asks if a.kind == "rent_reduction")
    assert "$3,050" in reduction.text


async def test_three_tone_drafts(client: AsyncClient) -> None:
    price, evidence = _price()
    ctx = LeverageContext(listing=_listing(rent=3200), price=price, price_evidence=evidence)
    bundle, all_points = await draft_negotiations(LLMService(), ctx)
    assert [d.tone for d in bundle.drafts] == ["friendly", "firm", "data-driven"]
    for draft in bundle.drafts:
        assert draft.subject
        assert "[Your name]" in draft.body
        assert draft.leverage_points
    # Tones actually differ
    bodies = {d.body for d in bundle.drafts}
    assert len(bodies) == 3


async def test_toggling_leverage_regenerates_without_it(client: AsyncClient) -> None:
    price, evidence = _price()
    ctx = LeverageContext(listing=_listing(rent=3200), price=price, price_evidence=evidence)
    _, all_points = await draft_negotiations(LLMService(), ctx)
    keep = [p.id for p in all_points[:1]]
    bundle, _ = await draft_negotiations(LLMService(), ctx, selected_leverage_ids=keep)
    assert all(len(d.leverage_points) == 1 for d in bundle.drafts)


async def test_negotiation_endpoint_with_lease(client: AsyncClient) -> None:
    await seed()
    generate_leases()
    # Run a search so price/review results exist for a listing.
    _, run_id = await _create_brief_and_run(client)
    detail = await _run_to_completion(client, run_id)
    listing_id = detail["report"]["ranked"][0]["listing_id"]

    # Attach a problematic sample lease to the listing.
    resp = await client.post(
        f"/api/leases/samples/lease_6_el_camino_kitchen_sink?listing_id={listing_id}"
    )
    lease_id = resp.json()["id"]
    await wait_for_lease(lease_id)

    resp = await client.post("/api/negotiations", json={"listing_id": listing_id})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    drafts = body["bundle"]["drafts"]
    assert len(drafts) == 3
    points = body["all_leverage_points"]
    kinds = {p["kind"] for p in points}
    assert "lease" in kinds  # redlines from the lease agent surfaced as leverage
    # every leverage point's evidence resolves in the evidence map
    for point in points:
        for evidence_id in point["evidence_ids"]:
            assert evidence_id in body["evidence"]
    assert any(a["kind"] == "clause_redline" for a in drafts[0]["asks"])
