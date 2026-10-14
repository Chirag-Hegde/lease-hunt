"""Shared API dependencies.

Auth: a Bearer JWT identifies the user; without one, demo mode falls back to
the shared demo user and production returns 401. Every query is scoped by
user_id, so each user sees only their own data."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import models
from app.db.session import get_db
from app.services.auth import verify_session_token

DEMO_USER_EMAIL = "demo@leasehunt.dev"

DbSession = Annotated[AsyncSession, Depends(get_db)]


async def _get_or_create(session: AsyncSession, email: str) -> models.User:
    user = (
        await session.execute(select(models.User).where(models.User.email == email))
    ).scalar_one_or_none()
    if user is None:
        user = models.User(email=email)
        session.add(user)
        await session.commit()
        await session.refresh(user)
    return user


async def get_current_user(request: Request, session: DbSession) -> models.User:
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        email = verify_session_token(auth_header.removeprefix("Bearer ").strip())
        if email is None:
            raise HTTPException(401, "invalid or expired token")
        return await _get_or_create(session, email)
    if get_settings().demo_mode:
        return await _get_or_create(session, DEMO_USER_EMAIL)
    raise HTTPException(401, "authentication required")


CurrentUser = Annotated[models.User, Depends(get_current_user)]
