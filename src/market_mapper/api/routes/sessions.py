"""Session routes for creating and reading research sessions."""

from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import Field

from market_mapper.auth import AuthenticatedUser, CurrentUser
from market_mapper.schemas.models import ResearchSession, WorkspaceSnapshot
from market_mapper.schemas.models.common import MarketMapperModel
from market_mapper.services import (
    ApprovedDashboardPayload,
    AuthorizationError,
    DashboardNotReadyError,
    SessionDeleteError,
    SessionNotFoundError,
    WorkflowService,
    WorkflowServiceError,
)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class CreateSessionRequest(MarketMapperModel):
    """Request body for creating a research session."""

    prompt: str = Field(min_length=1)


@router.post("", response_model=ResearchSession)
def create_session(
    request: CreateSessionRequest,
    user: AuthenticatedUser = CurrentUser,
) -> ResearchSession:
    """Create a durable research session from a top-level user prompt."""

    service = WorkflowService()
    try:
        return service.create_session(user_id=user.user_id, user_prompt=request.prompt)
    except WorkflowServiceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("", response_model=list[ResearchSession])
def list_sessions(user: AuthenticatedUser = CurrentUser) -> list[ResearchSession]:
    """List stored research sessions for the dashboard session rail."""

    service = WorkflowService()
    return service.list_sessions(user_id=user.user_id)


@router.get("/{session_id}", response_model=ResearchSession)
def get_session(session_id: str, user: AuthenticatedUser = CurrentUser) -> ResearchSession:
    """Fetch one stored research session."""

    service = WorkflowService()
    try:
        return service.get_session(session_id, user_id=user.user_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}") from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/{session_id}/dashboard", response_model=ApprovedDashboardPayload)
def get_dashboard(session_id: str, user: AuthenticatedUser = CurrentUser) -> ApprovedDashboardPayload:
    """Fetch the approved dashboard payload for a completed session."""

    service = WorkflowService()
    try:
        return service.get_approved_dashboard_payload(session_id, user_id=user.user_id)
    except DashboardNotReadyError as exc:
        raise HTTPException(
            status_code=404,
            detail=f"Approved dashboard state not found for session: {session_id}",
        ) from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/{session_id}/workspace", response_model=WorkspaceSnapshot)
def get_workspace(session_id: str, user: AuthenticatedUser = CurrentUser) -> WorkspaceSnapshot:
    """Fetch the live progressive workspace snapshot for a session."""

    service = WorkflowService()
    try:
        return service.get_workspace_snapshot(session_id, user_id=user.user_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}") from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.get("/{session_id}/stream")
async def stream_workspace(session_id: str, user: AuthenticatedUser = CurrentUser) -> StreamingResponse:
    """Stream live workspace, run status, and approved dashboard updates over SSE."""

    service = WorkflowService()
    try:
        service.get_session(session_id, user_id=user.user_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}") from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc

    async def event_stream():
        last_workspace = None
        last_run_status = None
        last_event_count = None
        approved_sent = False
        while True:
            try:
                workspace = service.get_workspace_snapshot(session_id, user_id=user.user_id)
                workspace_json = workspace.model_dump_json()
                if workspace_json != last_workspace:
                    yield f"event: workspace\ndata: {workspace_json}\n\n"
                    last_workspace = workspace_json
                if workspace.run_id:
                    run_status = service.get_run_status(workspace.run_id, user_id=user.user_id)
                    run_status_json = run_status.model_dump_json()
                    if run_status_json != last_run_status:
                        yield f"event: run_status\ndata: {run_status_json}\n\n"
                        last_run_status = run_status_json
                    run_events = service.get_run_events(workspace.run_id, user_id=user.user_id)
                    if last_event_count != len(run_events.events):
                        yield f"event: run_events\ndata: {run_events.model_dump_json()}\n\n"
                        last_event_count = len(run_events.events)
                if not approved_sent:
                    try:
                        approved = service.get_approved_dashboard_payload(session_id, user_id=user.user_id)
                    except DashboardNotReadyError:
                        approved = None
                    if approved is not None:
                        yield f"event: approved_dashboard\ndata: {approved.model_dump_json()}\n\n"
                        approved_sent = True
                        return
                await asyncio.sleep(1.0)
            except Exception as exc:  # pragma: no cover - runtime streaming path
                payload = json.dumps({"detail": str(exc)})
                yield f"event: error\ndata: {payload}\n\n"
                return

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.delete("/{session_id}", status_code=204, response_class=Response)
def delete_session(session_id: str, user: AuthenticatedUser = CurrentUser) -> Response:
    """Delete one stored research session and its durable outputs."""

    service = WorkflowService()
    try:
        service.delete_session(session_id, user_id=user.user_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}") from exc
    except SessionDeleteError as exc:
        raise HTTPException(status_code=500, detail=f"Session could not be deleted: {session_id}") from exc
    except AuthorizationError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return Response(status_code=204)
