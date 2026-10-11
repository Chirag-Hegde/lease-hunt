from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from app.api.deps import CurrentUser
from app.config import get_settings
from app.services.auth import create_session_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


class MagicLinkRequest(BaseModel):
    email: EmailStr


class MagicLinkResponse(BaseModel):
    message: str
    token: str | None = None  # returned directly only in demo mode


class MeResponse(BaseModel):
    email: str
    user_id: str


@router.post("/magic-link", response_model=MagicLinkResponse)
async def request_magic_link(body: MagicLinkRequest) -> MagicLinkResponse:
    """Demo mode returns the session token directly (no mail service);
    production would email a one-time link instead."""
    settings = get_settings()
    token = create_session_token(body.email)
    if settings.demo_mode:
        return MagicLinkResponse(
            message="Demo mode: use this token as a Bearer credential.", token=token
        )
    # Production: send the link via your mail provider; never return the token.
    raise HTTPException(
        501, "magic-link email delivery is not configured; set DEMO_MODE=true or wire a mailer"
    )


@router.get("/me", response_model=MeResponse)
async def me(user: CurrentUser) -> MeResponse:
    return MeResponse(email=user.email, user_id=user.id)
