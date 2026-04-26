"""Workflow execution and retrieval services for the Market Mapper API."""

from __future__ import annotations

import logging
from pathlib import Path

from pydantic import Field

from market_mapper.config.settings import get_settings
from market_mapper.schemas.models import (
    DashboardState,
    ResearchSession,
    RunEvent,
    SandboxArtifact,
    WorkspaceSnapshot,
    WorkflowRun,
)
from market_mapper.schemas.models.common import MarketMapperModel, RunStatus
from market_mapper.services.session_service import ApprovedSessionSnapshot, SessionStateService
from market_mapper.storage import FileWorkflowStateStore
from market_mapper.workflow import build_research_graph
from market_mapper.workflow.state import ResearchWorkflowState

logger = logging.getLogger("market_mapper.workflow_service")


class WorkflowServiceError(RuntimeError):
    """Base error for workflow service failures."""


class SessionNotFoundError(WorkflowServiceError):
    """Raised when a requested session cannot be found."""


class RunNotFoundError(WorkflowServiceError):
    """Raised when a requested run cannot be found."""


class DashboardNotReadyError(WorkflowServiceError):
    """Raised when approved dashboard outputs are not available yet."""


class SessionDeleteError(WorkflowServiceError):
    """Raised when a session cannot be deleted cleanly."""


class AuthorizationError(WorkflowServiceError):
    """Raised when a user tries to access another user's resources."""


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


class RunEventsResponse(MarketMapperModel):
    """API-friendly event feed for a workflow run."""

    run_id: str
    events: list[RunEvent] = Field(default_factory=list)


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

    def create_session(self, *, user_id: str, user_prompt: str) -> ResearchSession:
        normalized_prompt = user_prompt.strip()
        if not normalized_prompt:
            raise WorkflowServiceError("Session prompt must not be blank.")
        session = ResearchSession(
            user_id=user_id,
            user_prompt=normalized_prompt,
            normalized_prompt=normalized_prompt,
        )
        self.state_store.save_session(session)
        self.state_store.save_workspace_snapshot(
            WorkspaceSnapshot(
                session_id=session.id,
                user_id=session.user_id,
                run_id=None,
                session_status=session.status,
                prompt=session.user_prompt,
            )
        )
        return session

    def get_session(self, session_id: str, *, user_id: str | None = None) -> ResearchSession:
        try:
            session = self.state_store.load_session(session_id)
        except FileNotFoundError as exc:
            raise SessionNotFoundError(session_id) from exc
        if user_id and session.user_id != user_id:
            raise AuthorizationError(f"Session {session_id} is not available to this user.")
        return session

    def list_sessions(self, *, user_id: str) -> list[ResearchSession]:
        """Return all stored sessions, newest first for the dashboard rail."""

        return sorted(
            [session for session in self.state_store.list_sessions() if session.user_id == user_id],
            key=lambda session: session.updated_at,
            reverse=True,
        )

    def delete_session(self, session_id: str, *, user_id: str) -> None:
        """Delete a session and its durable workflow artifacts."""

        session = self.get_session(session_id, user_id=user_id)

        run_ids = list(session.run_ids)
        if session.active_run_id and session.active_run_id not in run_ids:
            run_ids.append(session.active_run_id)

        for run_id in run_ids:
            try:
                for sandbox_task in self.state_store.list_sandbox_tasks_for_run(run_id):
                    self.state_store.delete_sandbox_task(sandbox_task.id)
                for artifact in self.state_store.list_artifacts_for_run(run_id):
                    self.state_store.delete_artifact(artifact.id)
                self.state_store.delete_run(run_id)
            except FileNotFoundError:
                continue

        if session.dashboard_state_id:
            try:
                self.state_store.delete_dashboard_state(session.dashboard_state_id)
            except FileNotFoundError:
                pass
        try:
            self.state_store.delete_workspace_snapshot(session.id)
        except FileNotFoundError:
            pass

        self.session_state_service.delete_approved_snapshot(session.id)

        try:
            self.state_store.delete_session(session.id)
        except FileNotFoundError as exc:
            raise SessionDeleteError(session.id) from exc

    def create_run(self, session_id: str, *, user_id: str) -> WorkflowRun:
        session = self.get_session(session_id, user_id=user_id)
        run = WorkflowRun(session_id=session.id)
        session.attach_run(run.id, activate=True)
        session.status = RunStatus.RUNNING
        run.mark_running(current_node="planner")
        self.state_store.save_session(session)
        self.state_store.save_run(run)
        self.state_store.save_workspace_snapshot(
            WorkspaceSnapshot(
                session_id=session.id,
                user_id=session.user_id,
                run_id=run.id,
                session_status=session.status,
                prompt=session.user_prompt,
                research_plan=session.research_plan,
                current_node=run.current_node,
                completed_tasks=0,
                total_tasks=1,
                percent_complete=0.0,
            )
        )
        logger.info("Created workflow run %s for session %s.", run.id, session.id)
        return run

    def execute_run(self, run_id: str) -> WorkflowRun:
        try:
            run = self.state_store.load_run(run_id)
        except FileNotFoundError as exc:
            raise RunNotFoundError(run_id) from exc

        session = self.get_session(run.session_id)
        logger.info(
            "Executing workflow run %s for session %s with prompt: %s",
            run.id,
            session.id,
            session.user_prompt,
        )
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
            logger.exception("Workflow run %s failed before completion.", run.id)
            raise

        final_state.session.status = final_state.run.status
        self._persist_state(final_state)
        logger.info(
            "Workflow run %s finished with status %s.",
            final_state.run.id,
            final_state.run.status,
        )
        return final_state.run

    def start_run(self, session_id: str, *, user_id: str) -> WorkflowRun:
        run = self.create_run(session_id, user_id=user_id)
        return self.execute_run(run.id)

    def get_run_status(self, run_id: str, *, user_id: str) -> RunStatusResponse:
        try:
            run = self.state_store.load_run(run_id)
        except FileNotFoundError as exc:
            raise RunNotFoundError(run_id) from exc
        self.get_session(run.session_id, user_id=user_id)
        return RunStatusResponse(
            run=run,
            progress=self._build_progress(run),
        )

    def get_approved_dashboard(self, session_id: str, *, user_id: str) -> ApprovedSessionSnapshot:
        self.get_session(session_id, user_id=user_id)
        try:
            return self.session_state_service.load_approved_snapshot(session_id)
        except FileNotFoundError as exc:
            raise DashboardNotReadyError(session_id) from exc

    def get_approved_dashboard_payload(self, session_id: str, *, user_id: str) -> ApprovedDashboardPayload:
        snapshot = self.get_approved_dashboard(session_id, user_id=user_id)
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

    def get_workspace_snapshot(self, session_id: str, *, user_id: str) -> WorkspaceSnapshot:
        self.get_session(session_id, user_id=user_id)
        try:
            return self.state_store.load_workspace_snapshot(session_id)
        except FileNotFoundError:
            session = self.get_session(session_id, user_id=user_id)
            run = None
            if session.active_run_id:
                try:
                    run = self.state_store.load_run(session.active_run_id)
                except FileNotFoundError:
                    run = None
            return WorkspaceSnapshot(
                session_id=session.id,
                user_id=session.user_id,
                run_id=run.id if run is not None else None,
                session_status=session.status,
                prompt=session.user_prompt,
                research_plan=session.research_plan,
                current_node=run.current_node if run is not None else None,
                completed_tasks=0,
                total_tasks=1,
                percent_complete=0.0,
            )

    def get_run_events(self, run_id: str, *, user_id: str) -> RunEventsResponse:
        try:
            run = self.state_store.load_run(run_id)
        except FileNotFoundError as exc:
            raise RunNotFoundError(run_id) from exc
        self.get_session(run.session_id, user_id=user_id)

        events: list[RunEvent] = []
        for checkpoint in run.checkpoints:
            events.append(
                RunEvent(
                    run_id=run.id,
                    kind="checkpoint",
                    message=checkpoint.summary,
                    node_name=checkpoint.node_name,
                    created_at=checkpoint.created_at,
                    payload=checkpoint.payload,
                )
            )
        for task in run.agent_tasks:
            created_at = task.started_at or task.updated_at
            events.append(
                RunEvent(
                    run_id=run.id,
                    kind=f"task_{task.status.value}",
                    message=task.output_summary or f"{task.agent_name} {task.status.value.replace('_', ' ')}.",
                    node_name=task.task_type,
                    task_id=task.id,
                    created_at=created_at,
                    payload={
                        "agent_name": task.agent_name,
                        "task_type": task.task_type,
                        "status": task.status.value,
                    },
                )
            )
        events.sort(key=lambda event: event.created_at)
        return RunEventsResponse(run_id=run.id, events=events)

    def get_dashboard_state(self, session_id: str, *, user_id: str) -> DashboardState:
        session = self.get_session(session_id, user_id=user_id)
        if not session.dashboard_state_id:
            raise DashboardNotReadyError(session_id)
        try:
            return self.state_store.load_dashboard_state(session.dashboard_state_id)
        except FileNotFoundError as exc:
            raise DashboardNotReadyError(session_id) from exc

    def get_report_snapshot(self, report_id: str, *, user_id: str | None = None) -> ApprovedSessionSnapshot:
        snapshots_dir = self.session_state_service.snapshots_dir
        for path in snapshots_dir.glob("*.json"):
            snapshot = ApprovedSessionSnapshot.model_validate_json(path.read_text(encoding="utf-8"))
            if snapshot.report.id == report_id:
                if user_id and snapshot.user_id != user_id:
                    raise AuthorizationError(f"Report {report_id} is not available to this user.")
                return snapshot
        raise DashboardNotReadyError(report_id)

    def get_report_download(self, report_id: str, *, user_id: str) -> tuple[str, str | None]:
        snapshot = self.get_report_snapshot(report_id, user_id=user_id)
        report = snapshot.report
        if report.artifact_id:
            try:
                artifact = self.state_store.load_artifact(snapshot.run_id, report.artifact_id)
            except FileNotFoundError:
                artifact = None
            if artifact and artifact.path and Path(artifact.path).exists():
                return artifact.path, artifact.content_type
        return report.markdown_body, "text/markdown; charset=utf-8"

    def get_artifact(self, artifact_id: str, *, user_id: str) -> SandboxArtifact:
        try:
            artifact = self.state_store.load_artifact("", artifact_id)
        except FileNotFoundError as exc:
            raise DashboardNotReadyError(artifact_id) from exc
        run = self.state_store.load_run(artifact.run_id)
        self.get_session(run.session_id, user_id=user_id)
        return artifact

    def _persist_state(self, state: ResearchWorkflowState) -> None:
        if state.dashboard_state is not None:
            state.session.attach_dashboard(state.dashboard_state.id)
            self.state_store.save_dashboard_state(state.dashboard_state)
        if state.workspace_snapshot is not None:
            self.state_store.save_workspace_snapshot(state.workspace_snapshot)
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
