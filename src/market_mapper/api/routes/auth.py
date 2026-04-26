"""Authentication routes."""

from __future__ import annotations

from fastapi import APIRouter

from market_mapper.auth import AuthenticatedUser, CurrentUser

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/me", response_model=AuthenticatedUser)
def get_current_user(user: AuthenticatedUser = CurrentUser) -> AuthenticatedUser:
    """Return the currently authenticated user."""

    return user
