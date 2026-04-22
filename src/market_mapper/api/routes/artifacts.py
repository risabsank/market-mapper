"""Artifact routes for serving sandbox-produced files and metadata."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse

from market_mapper.services import DashboardNotReadyError, WorkflowService

router = APIRouter(prefix="/api/artifacts", tags=["artifacts"])


@router.get("/{artifact_id}")
def get_artifact(artifact_id: str):
    """Serve one persisted sandbox artifact by id."""

    service = WorkflowService()
    try:
        artifact = service.get_artifact(artifact_id)
    except DashboardNotReadyError as exc:
        raise HTTPException(status_code=404, detail=f"Artifact not found: {artifact_id}") from exc

    if artifact.path:
        path = Path(artifact.path)
        if path.exists():
            return FileResponse(
                path=path,
                media_type=artifact.content_type or "application/octet-stream",
                filename=path.name,
            )
    return PlainTextResponse(
        content=artifact.label,
        media_type="text/plain; charset=utf-8",
    )
