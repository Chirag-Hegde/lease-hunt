"""JWT auth. Demo mode: requests without a token act as the demo user.
Production: magic-link tokens (emailed) exchanged for session JWTs; every
query is scoped by user_id."""

from datetime import UTC, datetime, timedelta

import jwt

from app.config import get_settings

ALGORITHM = "HS256"


def create_session_token(email: str) -> str:
    settings = get_settings()
    payload = {
        "sub": email,
        "iat": datetime.now(UTC),
        "exp": datetime.now(UTC) + timedelta(hours=settings.jwt_ttl_hours),
        "type": "session",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def verify_session_token(token: str) -> str | None:
    """Return the email, or None when invalid/expired."""
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except jwt.InvalidTokenError:
        return None
    if payload.get("type") != "session":
        return None
    sub = payload.get("sub")
    return str(sub) if sub else None
