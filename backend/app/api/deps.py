"""Shared API dependencies. Demo mode: every request acts as the demo user.
Phase 9 adds JWT auth on top of the same dependency."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.db.session import get_db

DEMO_USER_EMAIL = "demo@leaselens.dev"

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(session: DbSession) -> models.User:
    user = (
        await session.execute(select(models.User).where(models.User.email == DEMO_USER_EMAIL))
    ).scalar_one_or_none()
    if user is None:
        user = models.User(email=DEMO_USER_EMAIL)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


CurrentUser = Annotated[models.User, Depends(get_current_user)]
