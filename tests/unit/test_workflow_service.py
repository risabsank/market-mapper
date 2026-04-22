from pathlib import Path

from market_mapper.schemas.models import (
    ArtifactKind,
    ComparisonResult,
    DashboardState,
    Report,
    ResearchSession,
    SandboxArtifact,
    WorkflowRun,
)
from market_mapper.services.session_service import SessionStateService
from market_mapper.services.workflow_service import WorkflowService
from market_mapper.storage import FileWorkflowStateStore
from market_mapper.workflow.state import ResearchWorkflowState


def test_workflow_service_start_run_persists_completed_state(monkeypatch, tmp_path: Path) -> None:
    store = FileWorkflowStateStore(tmp_path / "state")
    service = WorkflowService(
        state_store=store,
        session_state_service=SessionStateService(tmp_path / "state"),
    )
    session = service.create_session(user_prompt="Compare AI support platforms.")

    class FakeGraph:
        def invoke(self, state: ResearchWorkflowState) -> ResearchWorkflowState:
            state.run.mark_completed(current_node="session_chatbot")
            state.session.attach_run(state.run.id, activate=True)
            state.session.status = state.run.status
            state.dashboard_state = DashboardState(
                id="dashboard_1",
                session_id=state.session.id,
                run_id=state.run.id,
                executive_summary="Complete",
            )
            state.report = Report(
                id="report_1",
                run_id=state.run.id,
                title="Report",
                executive_summary="Summary",
                sections=[],
                markdown_body="# Report",
            )
            return state

    monkeypatch.setattr(
        "market_mapper.services.workflow_service.build_research_graph",
        lambda: FakeGraph(),
    )

    run = service.start_run(session.id)
    loaded_session = store.load_session(session.id)
    loaded_run = store.load_run(run.id)
    loaded_dashboard = store.load_dashboard_state("dashboard_1")

    assert run.status.value == "completed"
    assert loaded_run.current_node == "session_chatbot"
    assert loaded_session.active_run_id == run.id
    assert loaded_session.dashboard_state_id == "dashboard_1"
    assert loaded_dashboard.session_id == session.id


def test_workflow_service_report_download_falls_back_to_markdown(tmp_path: Path) -> None:
    store = FileWorkflowStateStore(tmp_path / "state")
    session_service = SessionStateService(tmp_path / "state")
    service = WorkflowService(
        state_store=store,
        session_state_service=session_service,
    )
    session = ResearchSession(id="session_1", user_prompt="Compare AI support tools.")
    run = WorkflowRun(id="run_1", session_id=session.id)
    snapshot = session_service.save_approved_snapshot(
        session=session,
        run=run,
        dashboard_state=DashboardState(id="dashboard_1", session_id=session.id, run_id=run.id),
        company_profiles=[],
        comparison_result=ComparisonResult(run_id=run.id),
        report=Report(
            id="report_1",
            run_id=run.id,
            title="Report",
            executive_summary="Summary",
            sections=[],
            markdown_body="# Report",
        ),
        chart_specs=[],
        source_documents=[],
    )

    payload, content_type = service.get_report_download(snapshot.report.id)

    assert payload == "# Report"
    assert content_type == "text/markdown; charset=utf-8"


def test_workflow_service_builds_dashboard_payload_with_artifact_urls(tmp_path: Path) -> None:
    store = FileWorkflowStateStore(tmp_path / "state")
    session_service = SessionStateService(tmp_path / "state")
    service = WorkflowService(
        state_store=store,
        session_state_service=session_service,
    )
    session = ResearchSession(id="session_1", user_prompt="Compare AI support tools.")
    run = WorkflowRun(id="run_1", session_id=session.id)
    chart_artifact = SandboxArtifact(
        id="artifact_chart_1",
        run_id=run.id,
        kind=ArtifactKind.CHART_IMAGE,
        label="Chart 1",
        path="/tmp/chart_1.svg",
    )
    dashboard_artifact = SandboxArtifact(
        id="artifact_dashboard_1",
        run_id=run.id,
        kind=ArtifactKind.DASHBOARD_PREVIEW,
        label="Dashboard Preview",
        path="/tmp/dashboard_state.json",
    )
    store.save_artifact(chart_artifact)
    store.save_artifact(dashboard_artifact)
    snapshot = session_service.save_approved_snapshot(
        session=session,
        run=run,
        dashboard_state=DashboardState(id="dashboard_1", session_id=session.id, run_id=run.id),
        company_profiles=[],
        comparison_result=ComparisonResult(run_id=run.id),
        report=Report(
            id="report_1",
            run_id=run.id,
            title="Report",
            executive_summary="Summary",
            sections=[],
            markdown_body="# Report",
        ),
        chart_specs=[],
        source_documents=[],
    )

    snapshot.chart_specs = []
    payload = service.get_approved_dashboard_payload(snapshot.session_id)

    assert payload.report_download_url.endswith("/api/reports/report_1/download")
    assert payload.dashboard_artifact is not None
    assert payload.dashboard_artifact.url.endswith("/api/artifacts/artifact_dashboard_1")
