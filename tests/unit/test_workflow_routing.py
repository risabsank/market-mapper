from market_mapper.schemas.models import ResearchPlan, ResearchSession, WorkflowRun
from market_mapper.workflow.routing import determine_next_route, select_executor_route
from market_mapper.workflow.state import ResearchWorkflowState


def test_determine_next_route_starts_with_planner() -> None:
    session = ResearchSession(user_prompt="Analyze AI support tools.")
    run = WorkflowRun(session_id=session.id)
    state = ResearchWorkflowState(session=session, run=run)

    assert determine_next_route(state) == "planner"


def test_determine_next_route_moves_to_discovery_after_plan() -> None:
    session = ResearchSession(
        user_prompt="Analyze AI support tools.",
        research_plan=ResearchPlan(market_query="AI support tools"),
    )
    run = WorkflowRun(session_id=session.id)
    state = ResearchWorkflowState(session=session, run=run)

    assert determine_next_route(state) == "company_discovery"


def test_select_executor_route_prefers_executor_decision() -> None:
    session = ResearchSession(
        user_prompt="Analyze AI support tools.",
        research_plan=ResearchPlan(market_query="AI support tools"),
    )
    run = WorkflowRun(session_id=session.id)
    state = ResearchWorkflowState(
        session=session,
        run=run,
        executor_route="web_research",
    )

    assert select_executor_route(state) == "web_research"
