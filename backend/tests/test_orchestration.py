"""Integration: full orchestration run in DEMO_MODE via the API."""

import asyncio
import json
from typing import Any

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


async def _run_to_completion(client: AsyncClient, run_id: str) -> dict[str, Any]:
    """Drive a run through any human-in-the-loop interrupts to a terminal state."""
    await runner.wait_for_run(run_id)
    for _ in range(3):
        resp = await client.get(f"/api/runs/{run_id}")
        detail: dict[str, Any] = resp.json()
        if detail["status"] != "interrupted":
            return detail
        resp = await client.post(f"/api/runs/{run_id}/resume", json={"approve": True})
        assert resp.status_code == 200, resp.text
        await runner.wait_for_run(run_id)
    resp = await client.get(f"/api/runs/{run_id}")
    return resp.json()  # type: ignore[no-any-return]


async def test_full_run_demo_mode(client: AsyncClient) -> None:
    await seed()
    _, run_id = await _create_brief_and_run(client)
    detail = await _run_to_completion(client, run_id)

    assert detail["status"] == "finished", detail.get("error")
    report = detail["report"]
    assert report is not None
    assert len(report["ranked"]) > 0
    assert report["formula"]
    top = report["ranked"][0]
    assert top["final_score"] > 0
    assert top["listing_id"] in detail["listings"]

    # Phase 4: commute + price agents ran per listing and have real scores.
    top_entry = detail["listings"][top["listing_id"]]
    assert top_entry["results"]["commute"]["status"] in ("ok", "partial")
    assert top_entry["results"]["commute"]["data"]["overall_score"] > 0
    assert top_entry["results"]["price"]["status"] in ("ok", "unavailable")
    assert top["scores"]["commute"] is not None

    # Isochrone bands for the primary place are in the report for the map.
    assert len(report["isochrones"]) >= 1
    geometry = report["isochrones"][0]["geojson"]["geometry"]
    assert geometry["type"] == "Polygon"

    # Scout respected the brief: dog friendly listings only.
    for entry in detail["listings"].values():
        assert "dog friendly" in entry["listing"]["amenities"]


async def test_interrupt_fires_and_limits_fanout(client: AsyncClient) -> None:
    await seed()
    _, run_id = await _create_brief_and_run(client)
    await runner.wait_for_run(run_id)

    resp = await client.get(f"/api/runs/{run_id}")
    detail = resp.json()
    assert detail["status"] == "interrupted"
    assert detail["interrupt"]["kind"] == "deep_analysis"
    assert detail["interrupt"]["listing_count"] > 8

    resp = await client.post(
        f"/api/runs/{run_id}/resume", json={"approve": True, "max_listings": 3}
    )
    assert resp.status_code == 200
    await runner.wait_for_run(run_id)

    resp = await client.get(f"/api/runs/{run_id}")
    detail = resp.json()
    assert detail["status"] == "finished", detail.get("error")
    analyzed = [entry for entry in detail["listings"].values() if "commute" in entry["results"]]
    assert len(analyzed) == 3


async def test_run_events_sse_stream(client: AsyncClient) -> None:
    await seed()
    _, run_id = await _create_brief_and_run(client)
    detail = await _run_to_completion(client, run_id)
    assert detail["status"] == "finished"

    events: list[dict[str, Any]] = []
    async with client.stream("GET", f"/api/runs/{run_id}/events") as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"].startswith("text/event-stream")

        async def consume() -> None:
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))

        await asyncio.wait_for(consume(), timeout=15)

    types = [e["type"] for e in events]
    assert types[0] == "run_started"
    assert "interrupt_required" in types
    assert "run_resumed" in types
    assert types[-1] == "run_finished"

    commute_events = [
        e for e in events if e["type"] == "agent_finished" and e["agent"] == "commute"
    ]
    assert len(commute_events) > 0
    assert all("listing_id" in e["payload"] for e in commute_events)
