"""Workflow execution and retrieval services for the Market Mapper API."""

from __future__ import annotations

from pathlib import Path

from pydantic import Field

from market_mapper.config.settings import get_settings
from market_mapper.schemas.models import DashboardState, ResearchSession, SandboxArtifact, WorkflowRun
from market_mapper.schemas.models.common import MarketMapperModel, RunStatus
from market_mapper.services.session_service import ApprovedSessionSnapshot, SessionStateService
from market_mapper.storage import FileWorkflowStateStore
from market_mapper.workflow import build_research_graph
from market_mapper.workflow.state import ResearchWorkflowState


class WorkflowServiceError(RuntimeError):
    """Base error for workflow service failures."""


class SessionNotFoundError(WorkflowServiceError):
    """Raised when a requested session cannot be found."""


class RunNotFoundError(WorkflowServiceError):
    """Raised when a requested run cannot be found."""


class DashboardNotReadyError(WorkflowServiceError):
    """Raised when approved dashboard outputs are not available yet."""


class RunProgress(MarketMapperModel):
    """Progress summary for a workflow run."""

    completed_tasks: int = 0
    total_tasks: int = 0
    current_node: str | None = None
    percent_complete: float = Field(default=0.0, ge=0.0, le=100.0)


class RunStatusResponse(MarketMapperModel):
    """API-friendly run status payload."""

    run: WorkflowRun
    progress: RunProgress


class ArtifactLink(MarketMapperModel):
    """API-safe artifact metadata plus retrieval URL."""

    artifact_id: str
    kind: str
    label: str
    content_type: str | None = None
    url: str


class ChartArtifactPayload(MarketMapperModel):
    """Chart spec plus its served artifact when available."""

    chart_id: str
    title: str
    chart_type: str
    description: str | None = None
    artifact: ArtifactLink | None = None


class ApprovedDashboardPayload(MarketMapperModel):
    """Approved dashboard snapshot enriched with artifact URLs."""

    snapshot: ApprovedSessionSnapshot
    report_download_url: str
    report_artifact: ArtifactLink | None = None
    dashboard_artifact: ArtifactLink | None = None
    chart_artifacts: list[ChartArtifactPayload] = Field(default_factory=list)


class WorkflowService:
    """Create sessions, execute workflow runs, and retrieve approved outputs."""

    def __init__(
        self,
        *,
        state_store: FileWorkflowStateStore | None = None,
        session_state_service: SessionStateService | None = None,
    ) -> None:
        settings = get_settings()
        self.state_store = state_store or FileWorkflowStateStore(settings.workflow_state_dir)
        self.session_state_service = session_state_service or SessionStateService(
            settings.workflow_state_dir
        )

    def create_session(self, *, user_prompt: str) -> ResearchSession:
        normalized_prompt = user_prompt.strip()
        if not normalized_prompt:
            raise WorkflowServiceError("Session prompt must not be blank.")
        session = ResearchSession(
            user_prompt=normalized_prompt,
            normalized_prompt=normalized_prompt,
        )
        self.state_store.save_session(session)
        return session

    def get_session(self, session_id: str) -> ResearchSession:
        try:
            return self.state_store.load_session(session_id)
        except FileNotFoundError as exc:
            raise SessionNotFoundError(session_id) from exc

    def start_run(self, session_id: str) -> WorkflowRun:
        session = self.get_session(session_id)
        run = WorkflowRun(session_id=session.id)
        session.attach_run(run.id, activate=True)
        session.status = RunStatus.RUNNING
        run.mark_running(current_node="planner")
        self.state_store.save_session(session)
        self.state_store.save_run(run)

        state = ResearchWorkflowState(
            session=session,
            run=run,
        )
        try:
            graph = build_research_graph()
            raw_result = graph.invoke(state)
            final_state = self._coerce_state(raw_result)
        except Exception as exc:
            run.mark_failed(str(exc), current_node=run.current_node or "planner")
            session.status = run.status
            self.state_store.save_run(run)
            self.state_store.save_session(session)
            raise

        final_state.session.status = final_state.run.status
        self._persist_state(final_state)
        return final_state.run

    def get_run_status(self, run_id: str) -> RunStatusResponse:
        try:
            run = self.state_store.load_run(run_id)
        except FileNotFoundError as exc:
            raise RunNotFoundError(run_id) from exc
        return RunStatusResponse(
            run=run,
            progress=self._build_progress(run),
        )

    def get_approved_dashboard(self, session_id: str) -> ApprovedSessionSnapshot:
        try:
            return self.session_state_service.load_approved_snapshot(session_id)
        except FileNotFoundError as exc:
            raise DashboardNotReadyError(session_id) from exc

    def get_approved_dashboard_payload(self, session_id: str) -> ApprovedDashboardPayload:
        snapshot = self.get_approved_dashboard(session_id)
        report_artifact = self._artifact_link(snapshot.report.artifact_id)
        dashboard_artifact = self._dashboard_artifact_link(snapshot.run_id)
        chart_artifacts = [
            ChartArtifactPayload(
                chart_id=chart_spec.id,
                title=chart_spec.title,
                chart_type=chart_spec.chart_type,
                description=chart_spec.description,
                artifact=self._artifact_link(chart_spec.artifact_id),
            )
            for chart_spec in snapshot.chart_specs
        ]
        return ApprovedDashboardPayload(
            snapshot=snapshot,
            report_download_url=f"/api/reports/{snapshot.report.id}/download",
            report_artifact=report_artifact,
            dashboard_artifact=dashboard_artifact,
            chart_artifacts=chart_artifacts,
        )

    def get_dashboard_state(self, session_id: str) -> DashboardState:
        session = self.get_session(session_id)
        if not session.dashboard_state_id:
            raise DashboardNotReadyError(session_id)
        try:
            return self.state_store.load_dashboard_state(session.dashboard_state_id)
        except FileNotFoundError as exc:
            raise DashboardNotReadyError(session_id) from exc

    def get_report_snapshot(self, report_id: str) -> ApprovedSessionSnapshot:
        snapshots_dir = self.session_state_service.snapshots_dir
        for path in snapshots_dir.glob("*.json"):
            snapshot = ApprovedSessionSnapshot.model_validate_json(path.read_text(encoding="utf-8"))
            if snapshot.report.id == report_id:
                return snapshot
        raise DashboardNotReadyError(report_id)

    def get_report_download(self, report_id: str) -> tuple[str, str | None]:
        snapshot = self.get_report_snapshot(report_id)
        report = snapshot.report
        if report.artifact_id:
            try:
                artifact = self.state_store.load_artifact(snapshot.run_id, report.artifact_id)
            except FileNotFoundError:
                artifact = None
            if artifact and artifact.path and Path(artifact.path).exists():
                return artifact.path, artifact.content_type
        return report.markdown_body, "text/markdown; charset=utf-8"

    def get_artifact(self, artifact_id: str) -> SandboxArtifact:
        try:
            return self.state_store.load_artifact("", artifact_id)
        except FileNotFoundError as exc:
            raise DashboardNotReadyError(artifact_id) from exc

    def _persist_state(self, state: ResearchWorkflowState) -> None:
        if state.dashboard_state is not None:
            state.session.attach_dashboard(state.dashboard_state.id)
            self.state_store.save_dashboard_state(state.dashboard_state)
        self.state_store.save_session(state.session)
        self.state_store.save_run(state.run)
        for sandbox_task in state.sandbox_tasks:
            self.state_store.save_sandbox_task(sandbox_task)
        for artifact in state.sandbox_artifacts:
            self.state_store.save_artifact(artifact)

    def _coerce_state(self, raw_result: object) -> ResearchWorkflowState:
        if isinstance(raw_result, ResearchWorkflowState):
            return raw_result
        if isinstance(raw_result, dict):
            return ResearchWorkflowState.model_validate(raw_result)
        raise WorkflowServiceError("Workflow graph returned an unexpected result type.")

    def _build_progress(self, run: WorkflowRun) -> RunProgress:
        completed_tasks = sum(1 for task in run.agent_tasks if task.status.value == "completed")
        total_tasks = max(len(run.agent_tasks), 1)
        percent_complete = 100.0 if run.status == RunStatus.COMPLETED else round(
            (completed_tasks / total_tasks) * 100.0,
            1,
        )
        return RunProgress(
            completed_tasks=completed_tasks,
            total_tasks=total_tasks,
            current_node=run.current_node,
            percent_complete=percent_complete,
        )

    def _artifact_link(self, artifact_id: str | None) -> ArtifactLink | None:
        if not artifact_id:
            return None
        try:
            artifact = self.get_artifact(artifact_id)
        except DashboardNotReadyError:
            return None
        return ArtifactLink(
            artifact_id=artifact.id,
            kind=artifact.kind.value if hasattr(artifact.kind, "value") else str(artifact.kind),
            label=artifact.label,
            content_type=artifact.content_type,
            url=f"/api/artifacts/{artifact.id}",
        )

    def _dashboard_artifact_link(self, run_id: str) -> ArtifactLink | None:
        artifacts = self.state_store.list_artifacts_for_run(run_id)
        for artifact in reversed(artifacts):
            artifact_kind = artifact.kind.value if hasattr(artifact.kind, "value") else str(artifact.kind)
            if artifact_kind == "dashboard_preview":
                return ArtifactLink(
                    artifact_id=artifact.id,
                    kind=artifact_kind,
                    label=artifact.label,
                    content_type=artifact.content_type,
                    url=f"/api/artifacts/{artifact.id}",
                )
        return None
