"""Contracts for sandbox-backed execution."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import Field

from market_mapper.schemas.models.common import ArtifactKind, MarketMapperModel


class SandboxFileArtifact(MarketMapperModel):
    """A file artifact emitted by sandbox execution before persistence."""

    kind: ArtifactKind
    label: str
    path: str
    content_type: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SandboxExecutionRequest(MarketMapperModel):
    """Request sent from the trusted harness to the sandbox runtime."""

    route_name: str
    run_id: str
    sandbox_task_id: str
    working_directory: str
    payload: dict[str, Any] = Field(default_factory=dict)


class SandboxExecutionResult(MarketMapperModel):
    """Result returned by sandbox execution."""

    sandbox_task_id: str
    route_name: str
    working_directory: str
    summary: str
    artifacts: list[SandboxFileArtifact] = Field(default_factory=list)
    log_path: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @property
    def working_dir_path(self) -> Path:
        return Path(self.working_directory)

