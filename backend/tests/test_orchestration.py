"""Integration: full orchestration run in DEMO_MODE via the API."""

import asyncio
import json

from httpx import AsyncClient

from app.graph import runner
from app.seed.load import seed


async def _create_brief_and_run(client: AsyncClient) -> tuple[str, str]:
    resp = await client.post(
        "/api/briefs",
        json={
            "text": "2b2b under $3,800 near Sunnyvale Caltrain, 20 min to Santa Clara, dog friendly"
        },
    )
    assert resp.status_code == 200, resp.text
    brief = resp.json()
    assert brief["data"]["budget_max"] == 3800

    resp = await client.post("/api/runs", json={"brief_id": brief["id"]})
    assert resp.status_code == 200, resp.text
    return brief["id"], resp.json()["run_id"]


async def test_full_run_demo_mode(client: AsyncClient) -> None:
    await seed()
    _, run_id = await _create_brief_and_run(client)
    await runner.wait_for_run(run_id)

    # Resume if the human-in-the-loop interrupt fired (it shouldn't with no
    # per-listing agents registered yet, but stay robust as phases land).
    for _ in range(3):
        resp = await client.get(f"/api/runs/{run_id}")
        detail = resp.json()
        if detail["status"] != "interrupted":
            break
        resp = await client.post(f"/api/runs/{run_id}/resume", json={"approve": True})
        assert resp.status_code == 200
        await runner.wait_for_run(run_id)

    assert detail["status"] == "finished", detail.get("error")
    report = detail["report"]
    assert report is not None
    assert len(report["ranked"]) > 0
    assert report["formula"]
    top = report["ranked"][0]
    assert top["final_score"] > 0
    assert top["listing_id"] in detail["listings"]

    # Scout respected the brief: dog friendly + within stretched budget.
    for entry in detail["listings"].values():
        assert "dog friendly" in entry["listing"]["amenities"]


async def test_run_events_sse_stream(client: AsyncClient) -> None:
    await seed()
    _, run_id = await _create_brief_and_run(client)
    await runner.wait_for_run(run_id)

    events: list[dict[str, object]] = []
    async with client.stream("GET", f"/api/runs/{run_id}/events") as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")

        async def consume() -> None:
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))

        await asyncio.wait_for(consume(), timeout=10)

    types = [e["type"] for e in events]
    assert types[0] == "run_started"
    assert "agent_started" in types
    assert "agent_finished" in types
    assert types[-1] == "run_finished"
    scout_finish = next(
        e for e in events if e["type"] == "agent_finished" and e["agent"] == "scout"
    )
    payload = scout_finish["payload"]
    assert isinstance(payload, dict)
    assert payload["status"] == "ok"
