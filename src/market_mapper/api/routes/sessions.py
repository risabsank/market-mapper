"""Session routes for creating and reading research sessions."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import Field

from market_mapper.schemas.models import ResearchSession
from market_mapper.schemas.models.common import MarketMapperModel
from market_mapper.services import (
    DashboardNotReadyError,
    SessionNotFoundError,
    WorkflowService,
    WorkflowServiceError,
)
from market_mapper.services.session_service import ApprovedSessionSnapshot

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class CreateSessionRequest(MarketMapperModel):
    """Request body for creating a research session."""

    prompt: str = Field(min_length=1)


@router.post("", response_model=ResearchSession)
def create_session(request: CreateSessionRequest) -> ResearchSession:
    """Create a durable research session from a top-level user prompt."""

    service = WorkflowService()
    try:
        return service.create_session(user_prompt=request.prompt)
    except WorkflowServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/{session_id}", response_model=ResearchSession)
def get_session(session_id: str) -> ResearchSession:
    """Fetch one stored research session."""

    service = WorkflowService()
    try:
        return service.get_session(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}") from exc


@router.get("/{session_id}/dashboard", response_model=ApprovedSessionSnapshot)
def get_dashboard(session_id: str) -> ApprovedSessionSnapshot:
    """Fetch the approved dashboard payload for a completed session."""

    service = WorkflowService()
    try:
        return service.get_approved_dashboard(session_id)
    except DashboardNotReadyError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Approved dashboard state not found for session: {session_id}",
        ) from exc
