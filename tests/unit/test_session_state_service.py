from market_mapper.schemas.models import (
    ComparisonResult,
    DashboardState,
    Report,
    ResearchPlan,
    ResearchSession,
    WorkflowRun,
)
from market_mapper.services.session_service import (
    DemoSessionChatRequest,
    SessionChatRequest,
    SessionStateService,
)


def test_session_state_service_persists_approved_snapshot(tmp_path) -> None:
    service = SessionStateService(root_dir=tmp_path)
    session = ResearchSession(
        id="session_1",
        user_id="demo-user",
        user_prompt="Compare AI support tools.",
        research_plan=ResearchPlan(market_query="AI support"),
    )
    run = WorkflowRun(id="run_1", session_id=session.id)
    snapshot = service.save_approved_snapshot(
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

    loaded = service.load_approved_snapshot(session.id)

    assert loaded.id == snapshot.id
    assert loaded.session_id == session.id
    assert loaded.run_id == run.id


def test_session_state_service_resolves_normal_chat_from_persisted_snapshot(tmp_path) -> None:
    service = SessionStateService(root_dir=tmp_path)
    session = ResearchSession(
        id="session_1",
        user_id="demo-user",
        user_prompt="Compare AI support tools.",
        research_plan=ResearchPlan(market_query="AI support"),
    )
    run = WorkflowRun(id="run_1", session_id=session.id)
    snapshot = service.save_approved_snapshot(
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

    resolved = service.resolve_chat_request(
        SessionChatRequest(session_id=session.id, question="What matters most?")
    )

    assert resolved.id == snapshot.id


def test_session_state_service_resolves_demo_chat_from_inline_snapshot(tmp_path) -> None:
    service = SessionStateService(root_dir=tmp_path)
    session = ResearchSession(
        id="session_1",
        user_id="demo-user",
        user_prompt="Compare AI support tools.",
        research_plan=ResearchPlan(market_query="AI support"),
    )
    run = WorkflowRun(id="run_1", session_id=session.id)
    snapshot = service.save_approved_snapshot(
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

    resolved = service.resolve_demo_chat_request(
        DemoSessionChatRequest(
            question="What matters most?",
            approved_state=snapshot,
        )
    )

    assert resolved.id == snapshot.id
