"""Typed workflow state for the planner-executor graph."""

from __future__ import annotations

from datetime import datetime

from pydantic import Field

from market_mapper.schemas.models import (
    ChartSpec,
    CompanyCandidate,
    CompanyProfile,
    ComparisonResult,
    DashboardState,
    Report,
    ResearchSession,
    SandboxArtifact,
    SandboxTask,
    SourceDocument,
    VerificationResult,
    WorkspaceSnapshot,
    WorkflowRun,
)
from market_mapper.schemas.models.common import MarketMapperModel, utc_now


class ResearchWorkflowState(MarketMapperModel):
    """In-memory and durable state shared across workflow nodes."""

    session: ResearchSession
    run: WorkflowRun
    executor_route: str | None = None
    executor_summary: str | None = None
    source_documents: list[SourceDocument] = Field(default_factory=list)
    company_candidates: list[CompanyCandidate] = Field(default_factory=list)
    company_profiles: list[CompanyProfile] = Field(default_factory=list)
    comparison_result: ComparisonResult | None = None
    verification_result: VerificationResult | None = None
    chart_specs: list[ChartSpec] = Field(default_factory=list)
    report: Report | None = None
    dashboard_state: DashboardState | None = None
    sandbox_tasks: list[SandboxTask] = Field(default_factory=list)
    sandbox_artifacts: list[SandboxArtifact] = Field(default_factory=list)
    workspace_snapshot: WorkspaceSnapshot | None = None
    updated_at: datetime = Field(default_factory=utc_now)

    def touch(self) -> None:
        self.updated_at = utc_now()
