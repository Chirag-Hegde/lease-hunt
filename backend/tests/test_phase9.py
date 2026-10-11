"""Compare, trace, auth, settings endpoints."""

from httpx import AsyncClient

from app.seed.load import seed
from tests.test_orchestration import _create_brief_and_run, _run_to_completion


async def test_compare_endpoint(client: AsyncClient) -> None:
    await seed()
    _, run_id = await _create_brief_and_run(client)
    detail = await _run_to_completion(client, run_id)
    ids = [e["listing_id"] for e in detail["report"]["ranked"][:3]]

    resp = await client.get(f"/api/compare?ids={','.join(ids)}")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["listings"]) == 3
    assert all("commute" in entry["results"] for entry in body["listings"])

    resp = await client.get("/api/compare?ids=only-one")
    assert resp.status_code == 422


async def test_trace_endpoint(client: AsyncClient) -> None:
    await seed()
    _, run_id = await _create_brief_and_run(client)
    await _run_to_completion(client, run_id)

    resp = await client.get(f"/api/runs/{run_id}/trace")
    assert resp.status_code == 200
    trace = resp.json()
    kinds = {span["kind"] for span in trace["spans"]}
    assert {"agent", "tool", "llm"} <= kinds
    agent_spans = [s for s in trace["spans"] if s["kind"] == "agent"]
    assert any(s["agent"] == "scout" for s in agent_spans)
    assert any(s["agent"] == "critic" for s in agent_spans)
    llm_spans = [s for s in trace["spans"] if s["kind"] == "llm"]
    assert all(s["model"] for s in llm_spans)
    assert all(s["prompt_version"] for s in llm_spans)


async def test_auth_token_scopes_data(client: AsyncClient) -> None:
    # Demo user creates a brief.
    resp = await client.post("/api/briefs", json={"text": "1 bed under $2,500 in Sunnyvale"})
    brief_id = resp.json()["id"]

    # A different signed-in user can't see it.
    resp = await client.post("/api/auth/magic-link", json={"email": "alice@example.com"})
    assert resp.status_code == 200
    token = resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    resp = await client.get("/api/auth/me", headers=headers)
    assert resp.json()["email"] == "alice@example.com"

    resp = await client.get(f"/api/briefs/{brief_id}", headers=headers)
    assert resp.status_code == 404  # scoped: not alice's brief

    resp = await client.get("/api/auth/me", headers={"Authorization": "Bearer bogus"})
    assert resp.status_code == 401


async def test_settings_endpoint(client: AsyncClient) -> None:
    resp = await client.get("/api/settings")
    assert resp.status_code == 200
    body = resp.json()
    assert body["demo_mode"] is True
    assert body["llm_provider"] == "mock"
    assert body["keys"]["anthropic"] is False

    resp = await client.patch("/api/settings", json={"run_budget_usd": 1.25})
    assert resp.status_code == 200
    assert resp.json()["run_budget_usd"] == 1.25

    resp = await client.patch("/api/settings", json={"llm_provider": "anthropic"})
    assert resp.status_code == 422  # no key configured
