"""Routing decisions for the planner-executor workflow."""

from __future__ import annotations

from market_mapper.workflow.contracts import WorkflowRoute
from market_mapper.workflow.state import ResearchWorkflowState


def determine_next_route(state: ResearchWorkflowState) -> WorkflowRoute:
    """Pick the next node based on the current workflow state."""

    if state.session.research_plan is None:
        return "planner"

    if not state.company_candidates:
        return "company_discovery"

    if not state.source_documents:
        return "web_research"

    if not state.company_profiles:
        return "structured_extraction"

    if state.comparison_result is None:
        return "comparison"

    if state.verification_result is None:
        return "critic_verifier"

    if state.verification_result.requires_retry:
        return _retry_route(state.verification_result.next_actions)

    if state.report is None:
        return "report_generation"

    if not state.chart_specs:
        return "chart_generation"

    if state.dashboard_state is None:
        return "dashboard_builder"

    return "session_chatbot"


def _retry_route(next_actions: list[str]) -> WorkflowRoute:
    joined = " ".join(next_actions).lower()
    if "discovery" in joined:
        return "company_discovery"
    if "research" in joined or "source" in joined:
        return "web_research"
    if "extract" in joined or "profile" in joined:
        return "structured_extraction"
    if "compare" in joined:
        return "comparison"
    return "executor"
