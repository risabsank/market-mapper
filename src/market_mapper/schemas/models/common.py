"""Shared types and helpers for Market Mapper schemas."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(UTC)


def make_id(prefix: str) -> str:
    """Create a readable prefixed identifier."""
    return f"{prefix}_{uuid4().hex}"


class MarketMapperModel(BaseModel):
    """Base model with consistent validation rules."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        populate_by_name=True,
    )


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    RETRYING = "retrying"
    WAITING_FOR_APPROVAL = "waiting_for_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class SandboxTaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    RESUMABLE = "resumable"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ArtifactKind(str, Enum):
    PAGE_SNAPSHOT = "page_snapshot"
    EXTRACTED_TEXT = "extracted_text"
    STRUCTURED_JSON = "structured_json"
    CSV_EXPORT = "csv_export"
    CHART_IMAGE = "chart_image"
    MARKDOWN_REPORT = "markdown_report"
    DASHBOARD_PREVIEW = "dashboard_preview"
    RUN_LOG = "run_log"
    OTHER = "other"


class VerificationSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


class RetryRecord(MarketMapperModel):
    """Tracks one retry attempt for a task or run."""

    attempt_number: int = Field(ge=1)
    reason: str
    requested_at: datetime = Field(default_factory=utc_now)
    requested_by: str | None = None


class ApprovalRecord(MarketMapperModel):
    """Tracks an approval decision for a run or task."""

    id: str = Field(default_factory=lambda: make_id("approval"))
    target_kind: str
    target_id: str
    label: str
    status: ApprovalStatus = ApprovalStatus.PENDING
    notes: str | None = None
    approved_by: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    decided_at: datetime | None = None

    def decide(
        self,
        *,
        approved: bool,
        approved_by: str | None = None,
        notes: str | None = None,
    ) -> None:
        self.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        self.approved_by = approved_by
        self.notes = notes
        self.decided_at = utc_now()


class WorkflowCheckpoint(MarketMapperModel):
    """Snapshot of a workflow's progress at a point in time."""

    id: str = Field(default_factory=lambda: make_id("checkpoint"))
    node_name: str
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)

