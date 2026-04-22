"""Research graph builder for the planner/executor workflow skeleton."""

from __future__ import annotations

from market_mapper.workflow.nodes import (
    chart_generation_node,
    company_discovery_node,
    comparison_node,
    critic_verifier_node,
    dashboard_builder_node,
    executor_node,
    planner_node,
    report_generation_node,
    session_chatbot_node,
    structured_extraction_node,
    web_research_node,
)
from market_mapper.workflow.routing import determine_next_route
from market_mapper.workflow.state import ResearchWorkflowState


def build_research_graph():
    """Build the LangGraph research workflow if LangGraph is available."""

    try:
        from langgraph.graph import END, START, StateGraph
    except ImportError as exc:  # pragma: no cover - import depends on local env
        raise RuntimeError(
            "LangGraph is not installed. Add the dependency before building the graph."
        ) from exc

    graph = StateGraph(ResearchWorkflowState)
    graph.add_node("planner", planner_node)
    graph.add_node("executor", executor_node)
    graph.add_node("company_discovery", company_discovery_node)
    graph.add_node("web_research", web_research_node)
    graph.add_node("structured_extraction", structured_extraction_node)
    graph.add_node("comparison", comparison_node)
    graph.add_node("critic_verifier", critic_verifier_node)
    graph.add_node("report_generation", report_generation_node)
    graph.add_node("chart_generation", chart_generation_node)
    graph.add_node("dashboard_builder", dashboard_builder_node)
    graph.add_node("session_chatbot", session_chatbot_node)

    graph.add_edge(START, "planner")
    graph.add_edge("planner", "executor")
    graph.add_conditional_edges(
        "executor",
        determine_next_route,
        {
            "planner": "planner",
            "company_discovery": "company_discovery",
            "web_research": "web_research",
            "structured_extraction": "structured_extraction",
            "comparison": "comparison",
            "critic_verifier": "critic_verifier",
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
        "report_generation": "executor",
        "chart_generation": "executor",
        "dashboard_builder": "executor",
        "session_chatbot": "end",
    }
