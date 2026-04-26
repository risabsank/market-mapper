"""Session, workflow, and dashboard state models."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import Field

from .company import CompanyProfile, SourceDocument
from .comparison import ComparisonResult, Report
from .common import (
    ApprovalRecord,
    MarketMapperModel,
    RetryRecord,
    RunStatus,
    TaskStatus,
    WorkflowCheckpoint,
    make_id,
    utc_now,
)


class ResearchPlan(MarketMapperModel):
    """Structured plan produced by the Research Planner."""

    id: str = Field(default_factory=lambda: make_id("plan"))
    market_query: str
    requested_company_count: int = Field(default=4, ge=1, le=10)
    named_companies: list[str] = Field(default_factory=list)
    geography: str | None = None
    target_segment: str | None = None
    discovery_criteria: list[str] = Field(default_factory=list)
    comparison_dimensions: list[str] = Field(default_factory=list)
    required_outputs: list[str] = Field(
        default_factory=lambda: ["dashboard", "markdown_report", "charts"]
    )
    assumptions: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def touch(self) -> None:
        self.updated_at = utc_now()


class AgentTask(MarketMapperModel):
    """One unit of work handled by a planner, executor, or specialist agent."""

    id: str = Field(default_factory=lambda: make_id("task"))
    run_id: str
    agent_name: str
    task_type: str
    status: TaskStatus = TaskStatus.PENDING
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    output_summary: str | None = None
    error_message: str | None = None
    depends_on_task_ids: list[str] = Field(default_factory=list)
    sandbox_task_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    approval_ids: list[str] = Field(default_factory=list)
    retry_history: list[RetryRecord] = Field(default_factory=list)
    retry_count: int = 0
    started_at: datetime | None = None
    updated_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None

    def mark_running(self) -> None:
        now = utc_now()
        if self.started_at is None:
            self.started_at = now
        self.status = TaskStatus.RUNNING
        self.updated_at = now
        self.error_message = None

    def mark_completed(
        self,
        *,
        outputs: dict[str, Any] | None = None,
        output_summary: str | None = None,
    ) -> None:
        now = utc_now()
        if outputs is not None:
            self.outputs = outputs
        self.output_summary = output_summary
        self.status = TaskStatus.COMPLETED
        self.updated_at = now
        self.completed_at = now
        self.error_message = None

    def mark_failed(self, error_message: str) -> None:
        self.status = TaskStatus.FAILED
        self.error_message = error_message
        self.updated_at = utc_now()

    def mark_waiting_for_approval(self) -> None:
        self.status = TaskStatus.WAITING_FOR_APPROVAL
        self.updated_at = utc_now()

    def request_retry(self, reason: str, requested_by: str | None = None) -> RetryRecord:
        self.retry_count += 1
        record = RetryRecord(
            attempt_number=self.retry_count,
            reason=reason,
            requested_by=requested_by,
        )
        self.retry_history.append(record)
        self.status = TaskStatus.RETRYING
        self.updated_at = utc_now()
        self.error_message = None
        self.completed_at = None
        return record

    def add_artifact(self, artifact_id: str) -> None:
        if artifact_id not in self.artifact_ids:
            self.artifact_ids.append(artifact_id)
            self.updated_at = utc_now()

    def add_sandbox_task(self, sandbox_task_id: str) -> None:
        if sandbox_task_id not in self.sandbox_task_ids:
            self.sandbox_task_ids.append(sandbox_task_id)
            self.updated_at = utc_now()

    def add_approval(self, approval_id: str) -> None:
        if approval_id not in self.approval_ids:
            self.approval_ids.append(approval_id)
            self.updated_at = utc_now()


class WorkflowRun(MarketMapperModel):
    """Durable workflow state for one execution of the research graph."""

    id: str = Field(default_factory=lambda: make_id("run"))
    session_id: str
    status: RunStatus = RunStatus.PENDING
    current_node: str | None = None
    error_message: str | None = None
    agent_tasks: list[AgentTask] = Field(default_factory=list)
    sandbox_task_ids: list[str] = Field(default_factory=list)
    artifact_ids: list[str] = Field(default_factory=list)
    approval_records: list[ApprovalRecord] = Field(default_factory=list)
    checkpoints: list[WorkflowCheckpoint] = Field(default_factory=list)
    retry_history: list[RetryRecord] = Field(default_factory=list)
    retry_count: int = 0
    created_at: datetime = Field(default_factory=utc_now)
    started_at: datetime | None = None
    updated_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None

    def touch(self) -> None:
        self.updated_at = utc_now()

    def mark_running(self, current_node: str | None = None) -> None:
        now = utc_now()
        if self.started_at is None:
            self.started_at = now
        self.status = RunStatus.RUNNING
        self.current_node = current_node
        self.updated_at = now
        self.error_message = None

    def mark_completed(self, current_node: str | None = None) -> None:
        now = utc_now()
        self.status = RunStatus.COMPLETED
        self.current_node = current_node
        self.updated_at = now
        self.completed_at = now
        self.error_message = None

    def mark_failed(self, error_message: str, current_node: str | None = None) -> None:
        self.status = RunStatus.FAILED
        self.current_node = current_node
        self.error_message = error_message
        self.updated_at = utc_now()

    def mark_waiting_for_approval(self, current_node: str | None = None) -> None:
        self.status = RunStatus.WAITING_FOR_APPROVAL
        self.current_node = current_node
        self.updated_at = utc_now()

    def request_retry(self, reason: str, requested_by: str | None = None) -> RetryRecord:
        self.retry_count += 1
        record = RetryRecord(
            attempt_number=self.retry_count,
            reason=reason,
            requested_by=requested_by,
        )
        self.retry_history.append(record)
        self.status = RunStatus.RUNNING
        self.updated_at = utc_now()
        self.completed_at = None
        return record

    def add_task(self, task: AgentTask) -> None:
        for index, existing in enumerate(self.agent_tasks):
            if existing.id == task.id:
                self.agent_tasks[index] = task
                self.touch()
                return
        self.agent_tasks.append(task)
        self.touch()

    def get_task(self, task_id: str) -> AgentTask:
        for task in self.agent_tasks:
            if task.id == task_id:
                return task
        raise KeyError(f"Unknown task id: {task_id}")

    def add_sandbox_task(self, sandbox_task_id: str) -> None:
        if sandbox_task_id not in self.sandbox_task_ids:
            self.sandbox_task_ids.append(sandbox_task_id)
            self.touch()

    def add_artifact(self, artifact_id: str) -> None:
        if artifact_id not in self.artifact_ids:
            self.artifact_ids.append(artifact_id)
            self.touch()

    def add_approval(self, approval: ApprovalRecord) -> None:
        self.approval_records.append(approval)
        self.touch()

    def add_checkpoint(
        self,
        *,
        node_name: str,
        summary: str,
        payload: dict[str, Any] | None = None,
    ) -> WorkflowCheckpoint:
        checkpoint = WorkflowCheckpoint(
            node_name=node_name,
            summary=summary,
            payload=payload or {},
        )
        self.checkpoints.append(checkpoint)
        self.current_node = node_name
        self.touch()
        return checkpoint


class DashboardSection(MarketMapperModel):
    """One renderable dashboard section."""

    key: str
    title: str
    summary: str | None = None
    content_refs: list[str] = Field(default_factory=list)


class DashboardState(MarketMapperModel):
    """Typed dashboard payload for one research session."""

    id: str = Field(default_factory=lambda: make_id("dashboard"))
    session_id: str
    run_id: str
    executive_summary: str | None = None
    selected_company_ids: list[str] = Field(default_factory=list)
    comparison_result_id: str | None = None
    report_id: str | None = None
    chart_ids: list[str] = Field(default_factory=list)
    source_document_ids: list[str] = Field(default_factory=list)
    sections: list[DashboardSection] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def touch(self) -> None:
        self.updated_at = utc_now()


WorkspaceSectionStatusValue = Literal["pending", "running", "complete", "blocked"]


class CompanyWorkspaceStatus(MarketMapperModel):
    """Incremental progress for one company while a run is in flight."""

    id: str = Field(default_factory=lambda: make_id("company_workspace"))
    company_candidate_id: str | None = None
    company_profile_id: str | None = None
    name: str
    website: str | None = None
    status: WorkspaceSectionStatusValue = "pending"
    summary: str | None = None
    source_document_ids: list[str] = Field(default_factory=list)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    missing_fields: list[str] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=utc_now)


class WorkspaceSectionStatus(MarketMapperModel):
    """Status for one dashboard/workflow section while the run is live."""

    key: str
    title: str
    status: WorkspaceSectionStatusValue = "pending"
    summary: str | None = None
    progress_percent: float = Field(default=0.0, ge=0.0, le=100.0)
    content_refs: list[str] = Field(default_factory=list)


class WorkspaceSnapshot(MarketMapperModel):
    """Durable progressive snapshot used before the final approved dashboard is ready."""

    id: str = Field(default_factory=lambda: make_id("workspace"))
    session_id: str
    user_id: str
    run_id: str | None = None
    session_status: RunStatus = RunStatus.PENDING
    prompt: str
    research_plan: ResearchPlan | None = None
    current_node: str | None = None
    completed_tasks: int = 0
    total_tasks: int = 0
    percent_complete: float = Field(default=0.0, ge=0.0, le=100.0)
    company_statuses: list[CompanyWorkspaceStatus] = Field(default_factory=list)
    source_documents: list[SourceDocument] = Field(default_factory=list)
    company_profiles: list[CompanyProfile] = Field(default_factory=list)
    comparison_result: ComparisonResult | None = None
    report: Report | None = None
    chart_count: int = 0
    dashboard_ready: bool = False
    sections: list[WorkspaceSectionStatus] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def touch(self) -> None:
        self.updated_at = utc_now()


class RunEvent(MarketMapperModel):
    """API-facing event in the lifecycle of a workflow run."""

    id: str = Field(default_factory=lambda: make_id("event"))
    run_id: str
    kind: str
    message: str
    node_name: str | None = None
    task_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    payload: dict[str, Any] = Field(default_factory=dict)


class ResearchSession(MarketMapperModel):
    """Top-level session state for one user research prompt."""

    id: str = Field(default_factory=lambda: make_id("session"))
    user_id: str
    user_prompt: str
    normalized_prompt: str | None = None
    status: RunStatus = RunStatus.PENDING
    research_plan: ResearchPlan | None = None
    active_run_id: str | None = None
    run_ids: list[str] = Field(default_factory=list)
    dashboard_state_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    def touch(self) -> None:
        self.updated_at = utc_now()

    def attach_run(self, run_id: str, *, activate: bool = True) -> None:
        if run_id not in self.run_ids:
            self.run_ids.append(run_id)
        if activate:
            self.active_run_id = run_id
        self.touch()

    def attach_dashboard(self, dashboard_state_id: str) -> None:
        self.dashboard_state_id = dashboard_state_id
        self.touch()
