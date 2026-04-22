"""Report routes for retrieving dashboard outputs and Markdown downloads."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse

from market_mapper.schemas.models import Report
from market_mapper.services import DashboardNotReadyError, WorkflowService

router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("/{report_id}", response_model=Report)
def get_report(report_id: str) -> Report:
    """Fetch one generated report by id."""

    service = WorkflowService()
    try:
        return service.get_report_snapshot(report_id).report
    except DashboardNotReadyError as exc:
        raise HTTPException(status_code=404, detail=f"Report not found: {report_id}") from exc


@router.get("/{report_id}/download")
def download_report(report_id: str):
    """Download the Markdown report artifact when available."""

    service = WorkflowService()
    try:
        payload, content_type = service.get_report_download(report_id)
    except DashboardNotReadyError as exc:
        raise HTTPException(status_code=404, detail=f"Report not found: {report_id}") from exc

    path = Path(payload)
    if path.exists():
        return FileResponse(
            path=path,
            media_type=content_type or "text/markdown",
            filename=f"{report_id}.md",
        )
    return PlainTextResponse(
        content=payload,
        media_type=content_type or "text/markdown",
        headers={"Content-Disposition": f'attachment; filename="{report_id}.md"'},
    )
