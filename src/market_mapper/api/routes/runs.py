"""Workflow run routes for starting and inspecting research execution."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from market_mapper.schemas.models import WorkflowRun
from market_mapper.services import (
    RunNotFoundError,
    RunStatusResponse,
    SessionNotFoundError,
    WorkflowService,
)

router = APIRouter(tags=["runs"])


@router.post("/api/sessions/{session_id}/runs", response_model=WorkflowRun)
def start_run(session_id: str) -> WorkflowRun:
    """Start a workflow run for an existing research session."""

    service = WorkflowService()
    try:
        return service.start_run(session_id)
    except SessionNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}") from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Workflow run failed: {exc}") from exc


@router.get("/api/runs/{run_id}", response_model=RunStatusResponse)
def get_run_status(run_id: str) -> RunStatusResponse:
    """Fetch run status and progress for one workflow run."""

    service = WorkflowService()
    try:
        return service.get_run_status(run_id)
    except RunNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}") from exc
