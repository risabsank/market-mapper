"""OpenAI-powered Workflow Executor implementation."""

from __future__ import annotations

from market_mapper.schemas.models.common import MarketMapperModel
from market_mapper.services import generate_structured_output, render_agent_input
from market_mapper.workflow.contracts import (
    ExecutorNodeInput,
    ExecutorNodeOutput,
    WorkflowRoute,
)
from market_mapper.workflow.routing import determine_next_route


class ExecutorDecision(MarketMapperModel):
    """Structured executor decision returned by OpenAI."""

    next_route: WorkflowRoute
    summary: str
    retry_requested: bool = False
    retry_reason: str | None = None
    retry_target_route: WorkflowRoute | None = None
    needs_sandbox: bool = False
    sandbox_purpose: str | None = None


EXECUTOR_SYSTEM_PROMPT = """
You are the Workflow Executor for Market Mapper.

Choose the next route for the workflow based on the current structured state.

Rules:
- Only choose one of the allowed routes provided in the input.
- Prefer the earliest missing dependency in the workflow.
- If verification requires retry, route back to the most relevant missing stage.
- If the next step would benefit from isolated execution, set needs_sandbox=true and provide a short sandbox_purpose.
- Keep the summary short and operational.
"""


SANDBOX_ROUTE_DEFAULTS: dict[WorkflowRoute, str] = {
    "web_research": "Collect and snapshot public web pages for source-backed research.",
    "structured_extraction": "Transform extracted research artifacts into normalized structured data.",
    "critic_verifier": "Run artifact-backed validation over structured research outputs.",
    "report_generation": "Render and validate Markdown report artifacts.",
    "chart_generation": "Render chart data and reproducible chart artifacts.",
    "dashboard_builder": "Assemble dashboard preview artifacts from approved outputs.",
}


def run_workflow_executor(node_input: ExecutorNodeInput) -> ExecutorNodeOutput:
    """Choose the next workflow node using OpenAI, with deterministic fallback."""

    deterministic_route = determine_next_route(node_input.state)
    allowed_routes: list[WorkflowRoute] = [
        "planner",
        "company_discovery",
        "web_research",
        "structured_extraction",
        "comparison",
        "critic_verifier",
        "report_generation",
        "chart_generation",
        "dashboard_builder",
        "session_chatbot",
        "end",
    ]
    decision = generate_structured_output(
        response_model=ExecutorDecision,
        system_prompt=EXECUTOR_SYSTEM_PROMPT,
        user_input=render_agent_input(
            task_description="Choose the next route for the workflow.",
            context={
                "current_node": node_input.current_node,
                "allowed_routes": allowed_routes,
                "deterministic_fallback_route": deterministic_route,
                "state_summary": {
                    "has_plan": node_input.state.session.research_plan is not None,
                    "company_candidate_count": len(node_input.state.company_candidates),
                    "source_document_count": len(node_input.state.source_documents),
                    "company_profile_count": len(node_input.state.company_profiles),
                    "has_comparison_result": node_input.state.comparison_result is not None,
                    "has_verification_result": node_input.state.verification_result is not None,
                    "verification_requires_retry": (
                        node_input.state.verification_result.requires_retry
                        if node_input.state.verification_result
                        else False
                    ),
                    "has_report": node_input.state.report is not None,
                    "chart_count": len(node_input.state.chart_specs),
                    "has_dashboard_state": node_input.state.dashboard_state is not None,
                },
            },
        ),
    )
    route = decision.next_route if decision.next_route in allowed_routes else deterministic_route
    retry_requested = bool(
        node_input.state.verification_result
        and node_input.state.verification_result.requires_retry
        and route != "end"
    )
    retry_reason = (
        "; ".join(node_input.state.verification_result.next_actions)
        if retry_requested and node_input.state.verification_result.next_actions
        else decision.retry_reason
    )
    retry_target_route = route if retry_requested else decision.retry_target_route
    sandbox_purpose = decision.sandbox_purpose or SANDBOX_ROUTE_DEFAULTS.get(route)
    needs_sandbox = bool(decision.needs_sandbox or route in SANDBOX_ROUTE_DEFAULTS)
    return ExecutorNodeOutput(
        next_route=route,
        summary=decision.summary,
        current_node=node_input.current_node,
        retry_requested=retry_requested,
        retry_reason=retry_reason,
        retry_target_route=retry_target_route,
        needs_sandbox=needs_sandbox,
        sandbox_purpose=sandbox_purpose,
        checkpoint_payload={
            "next_route": route,
            "retry_requested": retry_requested,
            "retry_target_route": retry_target_route,
            "needs_sandbox": needs_sandbox,
            "sandbox_purpose": sandbox_purpose,
        },
    )
