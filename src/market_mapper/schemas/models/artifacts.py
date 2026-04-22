"""Sandbox task and artifact models."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from .common import (
    ArtifactKind,
    MarketMapperModel,
    RetryRecord,
    SandboxTaskStatus,
    make_id,
    utc_now,
)


class SandboxArtifact(MarketMapperModel):
    """Durable artifact emitted by a sandbox-backed task."""

    id: str = Field(default_factory=lambda: make_id("artifact"))
    run_id: str
    kind: ArtifactKind
    label: str
    path: str | None = None
    content_type: str | None = None
    source_task_id: str | None = None
    metadata: dict[str, str] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)


class SandboxTask(MarketMapperModel):
    """One isolated execution task launched from the workflow executor."""

    id: str = Field(default_factory=lambda: make_id("sandbox"))
    run_id: str
    purpose: str
    route_name: str | None = None
    status: SandboxTaskStatus = SandboxTaskStatus.PENDING
    agent_task_id: str | None = None
    command: str | None = None
    working_directory: str | None = None
    input_paths: list[str] = Field(default_factory=list)
    output_paths: list[str] = Field(default_factory=list)
    allowed_network_domains: list[str] = Field(default_factory=list)
    retry_history: list[RetryRecord] = Field(default_factory=list)
    retry_count: int = 0
    artifact_ids: list[str] = Field(default_factory=list)
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    updated_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None

    def mark_running(self) -> None:
        now = utc_now()
        if self.started_at is None:
            self.started_at = now
        self.status = SandboxTaskStatus.RUNNING
        self.updated_at = now
        self.error_message = None

    def mark_completed(self) -> None:
        now = utc_now()
        self.status = SandboxTaskStatus.COMPLETED
        self.updated_at = now
        self.completed_at = now
        self.error_message = None

    def mark_failed(self, error_message: str, *, resumable: bool = True) -> None:
        self.status = (
            SandboxTaskStatus.RESUMABLE if resumable else SandboxTaskStatus.FAILED
        )
        self.error_message = error_message
        self.updated_at = utc_now()

    def request_retry(self, reason: str, requested_by: str | None = None) -> RetryRecord:
        self.retry_count += 1
        record = RetryRecord(
            attempt_number=self.retry_count,
            reason=reason,
            requested_by=requested_by,
        )
        self.retry_history.append(record)
        self.status = SandboxTaskStatus.PENDING
        self.updated_at = utc_now()
        self.completed_at = None
        self.error_message = None
        return record

    def add_artifact(self, artifact_id: str) -> None:
        if artifact_id not in self.artifact_ids:
            self.artifact_ids.append(artifact_id)
            self.updated_at = utc_now()
