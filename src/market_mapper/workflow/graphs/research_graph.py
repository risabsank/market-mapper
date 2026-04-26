"""Research graph builder for the planner/executor workflow skeleton."""

from __future__ import annotations

import logging

from market_mapper.workflow.nodes import (
    chart_generation_node,
    company_discovery_node,
    comparison_node,
    critic_verifier_node,
    dashboard_builder_node,
    executor_node,
    output_generation_node,
    planner_node,
    report_generation_node,
    session_chatbot_node,
    structured_extraction_node,
    web_research_node,
)
from market_mapper.workflow.helpers import persist_failed_workflow_state, persist_workflow_state
from market_mapper.workflow.routing import select_executor_route
from market_mapper.workflow.state import ResearchWorkflowState

logger = logging.getLogger("market_mapper.workflow")


def _wrap_node(node_name: str, node_fn):
    """Wrap a workflow node with logging and persistence."""

    def wrapped(state: ResearchWorkflowState) -> ResearchWorkflowState:
        logger.info("Run %s entering node %s.", state.run.id, node_name)
        try:
            updated_state = node_fn(state)
            persist_workflow_state(updated_state)
            logger.info("Run %s finished node %s.", updated_state.run.id, node_name)
            return updated_state
        except Exception as exc:
            persist_failed_workflow_state(
                state,
                current_node=node_name,
                error_message=str(exc),
            )
            raise

    return wrapped


def build_research_graph():
    """Build the LangGraph research workflow if LangGraph is available."""

    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:  # pragma: no cover - import depends on local env
        raise RuntimeError(
            "LangGraph is not installed. Add the dependency before building the graph."
        ) from exc

    graph = StateGraph(ResearchWorkflowState)
    graph.add_node("planner", _wrap_node("planner", planner_node))
    graph.add_node("executor", _wrap_node("executor", executor_node))
    graph.add_node("company_discovery", _wrap_node("company_discovery", company_discovery_node))
    graph.add_node("web_research", _wrap_node("web_research", web_research_node))
    graph.add_node("structured_extraction", _wrap_node("structured_extraction", structured_extraction_node))
    graph.add_node("comparison", _wrap_node("comparison", comparison_node))
    graph.add_node("critic_verifier", _wrap_node("critic_verifier", critic_verifier_node))
    graph.add_node("output_generation", _wrap_node("output_generation", output_generation_node))
    graph.add_node("report_generation", _wrap_node("report_generation", report_generation_node))
    graph.add_node("chart_generation", _wrap_node("chart_generation", chart_generation_node))
    graph.add_node("dashboard_builder", _wrap_node("dashboard_builder", dashboard_builder_node))
    graph.add_node("session_chatbot", _wrap_node("session_chatbot", session_chatbot_node))

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "executor")
    graph.add_conditional_edges(
        "executor",
        select_executor_route,
        {
            "planner": "planner",
            "executor": "executor",
            "company_discovery": "company_discovery",
            "web_research": "web_research",
            "structured_extraction": "structured_extraction",
            "comparison": "comparison",
            "critic_verifier": "critic_verifier",
            "output_generation": "output_generation",
            "report_generation": "report_generation",
            "chart_generation": "chart_generation",
            "dashboard_builder": "dashboard_builder",
            "session_chatbot": "session_chatbot",
            "end": END,
        },
    )
    graph.add_edge("company_discovery", "executor")
    graph.add_edge("web_research", "executor")
    graph.add_edge("structured_extraction", "executor")
    graph.add_edge("comparison", "executor")
    graph.add_edge("critic_verifier", "executor")
    graph.add_edge("output_generation", "executor")
    graph.add_edge("report_generation", "executor")
    graph.add_edge("chart_generation", "executor")
    graph.add_edge("dashboard_builder", "executor")
    graph.add_edge("session_chatbot", END)
    return graph.compile()


def graph_routes() -> dict[str, str]:
    """Expose the skeleton routes for inspection without importing LangGraph."""

    return {
        "start": "planner",
        "planner": "executor",
        "executor": "conditional",
        "company_discovery": "executor",
        "web_research": "executor",
        "structured_extraction": "executor",
        "comparison": "executor",
        "critic_verifier": "executor",
        "output_generation": "executor",
        "report_generation": "executor",
        "chart_generation": "executor",
        "dashboard_builder": "executor",
        "session_chatbot": "end",
    }
