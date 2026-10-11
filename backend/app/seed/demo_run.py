"""Run one complete orchestration against the demo brief and persist it, so
the landing page's 'Try the demo' is instant."""

from sqlalchemy import select

from app.agents.contracts import Place, SearchBriefInput
from app.db import models
from app.db.session import get_session_factory, init_db
from app.graph import runner
from app.graph.context import create_run_context
from app.seed.load import DEMO_USER_EMAIL

DEMO_BRIEF_TEXT = "2b2b under $3,800 near Sunnyvale Caltrain, 20 min to Santa Clara, dog friendly"


def demo_brief() -> SearchBriefInput:
    return SearchBriefInput(
        budget_max=3800,
        beds=2,
        baths=2,
        pets=["dog"],
        cities=["Sunnyvale", "Santa Clara"],
        nice_to_haves=["in-unit laundry", "parking"],
        important_places=[
            Place(
                label="Work (Santa Clara)",
                address="Santa Clara",
                lat=37.3541,
                lng=-121.9552,
                weight=1.0,
                modes=["drive", "transit"],
                arrival_time="09:00",
                tolerance_minutes=20,
            ),
            Place(
                label="Sunnyvale Caltrain",
                address="Sunnyvale Caltrain",
                lat=37.3783,
                lng=-122.0306,
                weight=0.5,
                modes=["walk", "bike"],
                tolerance_minutes=15,
            ),
        ],
    )


async def run_demo() -> str:
    """Create (or reuse) the demo brief, run the full graph, return run_id."""
    await init_db()
    brief = demo_brief()
    async with get_session_factory()() as session:
        user = (
            await session.execute(select(models.User).where(models.User.email == DEMO_USER_EMAIL))
        ).scalar_one_or_none()
        if user is None:
            user = models.User(email=DEMO_USER_EMAIL)
            session.add(user)
            await session.flush()
        brief_row = models.SearchBrief(
            user_id=user.id, raw_text=DEMO_BRIEF_TEXT, data=brief.model_dump(mode="json")
        )
        session.add(brief_row)
        await session.flush()
        run = models.Run(brief_id=brief_row.id, user_id=user.id, status="pending")
        session.add(run)
        await session.commit()
        run_id, brief_id, user_id = run.id, brief_row.id, user.id

    create_run_context(run_id, user_id, brief_id, brief)
    await runner.launch_run(run_id)
    await runner.wait_for_run(run_id)

    async with get_session_factory()() as session:
        run_row = (
            await session.execute(select(models.Run).where(models.Run.id == run_id))
        ).scalar_one()
        # The demo must never block on a human-in-the-loop prompt.
        if run_row.status == "interrupted":
            await runner.resume_run(run_id, {"approve": True})
            await runner.wait_for_run(run_id)
            await session.refresh(run_row)
        print(f"demo run {run_id}: {run_row.status}, cost=${run_row.cost_usd:.4f}")
    return run_id
