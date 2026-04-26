"""Authentication and current-user resolution for Market Mapper."""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Query

from market_mapper.config.settings import get_settings
from market_mapper.schemas.models.common import MarketMapperModel


class AuthenticatedUser(MarketMapperModel):
    """Resolved user identity for one API request."""

    user_id: str
    display_name: str
    token: str


def require_current_user(
    authorization: str | None = Header(default=None),
    access_token: str | None = Query(default=None),
) -> AuthenticatedUser:
    """Resolve the current API user from a bearer token or query token."""

    token = access_token
    if authorization and authorization.lower().startswith("bearer "):
        token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required.")

    settings = get_settings()
    user_id = settings.auth_tokens.get(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid access token.")
    return AuthenticatedUser(
        user_id=user_id,
        display_name=user_id.replace("-", " ").title(),
        token=token,
    )


CurrentUser = Depends(require_current_user)
