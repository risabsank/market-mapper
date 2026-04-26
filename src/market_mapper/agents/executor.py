"""OpenAI-powered Workflow Executor implementation."""

from __future__ import annotations

import logging

from market_mapper.config.settings import get_settings
from market_mapper.schemas.models.common import MarketMapperModel
from market_mapper.services import generate_structured_output, render_agent_input
from market_mapper.workflow.contracts import (
    ExecutorNodeInput,
    ExecutorNodeOutput,
    WorkflowRoute,
)
from market_mapper.workflow.routing import determine_next_route

logger = logging.getLogger("market_mapper.executor")


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

    settings = get_settings()
    deterministic_route = determine_next_route(node_input.state)
    allowed_routes: list[WorkflowRoute] = [
        "planner",
        "company_discovery",
        "web_research",
        "structured_extraction",
        "comparison",
        "critic_verifier",
        "output_generation",
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
    retry_cap_reached = False
    capped_route: WorkflowRoute | None = None
    retry_target_route: WorkflowRoute | None = None
    retry_requested = bool(
        node_input.state.verification_result
        and node_input.state.verification_result.requires_retry
        and deterministic_route != "end"
    )
    if retry_requested and deterministic_route in {"web_research", "structured_extraction", "comparison"}:
        retry_target_route = deterministic_route
        retry_attempts = _count_route_attempts(node_input, deterministic_route)
        if retry_attempts >= settings.max_research_retries:
            retry_cap_reached = True
            retry_requested = False
            capped_route = _determine_post_retry_route(node_input)
            logger.warning(
                "Retry cap reached for route %s on run %s after %s retries. Continuing with %s.",
                deterministic_route,
                node_input.state.run.id,
                retry_attempts,
                capped_route,
            )
            deterministic_route = capped_route
    model_route = decision.next_route if decision.next_route in allowed_routes else deterministic_route
    route = deterministic_route
    if retry_requested and model_route == deterministic_route:
        route = model_route
    elif retry_requested and model_route != deterministic_route:
        logger.warning(
            "Executor model suggested retry route %s but deterministic retry route is %s for run %s. Using deterministic route.",
            model_route,
            deterministic_route,
            node_input.state.run.id,
        )
    elif model_route != deterministic_route:
        logger.info(
            "Executor model suggested route %s but workflow state requires %s for run %s. Using deterministic route.",
            model_route,
            deterministic_route,
            node_input.state.run.id,
        )

    if retry_requested and node_input.state.verification_result.next_actions:
        retry_reason = "; ".join(node_input.state.verification_result.next_actions)
    elif retry_cap_reached and retry_target_route is not None:
        retry_reason = (
            f"Retry cap reached for {retry_target_route.replace('_', ' ')} after "
            f"{settings.max_research_retries} retries. Proceeding with available evidence."
        )
    else:
        retry_reason = decision.retry_reason
    retry_target_route = route if retry_requested else retry_target_route if retry_cap_reached else None
    sandbox_purpose = decision.sandbox_purpose or SANDBOX_ROUTE_DEFAULTS.get(route)
    needs_sandbox = bool(decision.needs_sandbox or route in SANDBOX_ROUTE_DEFAULTS)
    summary = decision.summary
    parallel_company_count = (
        len(node_input.state.company_candidates)
        if route in {"web_research", "structured_extraction"} and node_input.state.company_candidates
        else 0
    )
    if model_route != deterministic_route:
        summary = (
            f"{decision.summary} State-authoritative routing selected {route}."
            if decision.summary
            else f"State-authoritative routing selected {route}."
        )
    if parallel_company_count > 1:
        parallel_summary = (
            f"Launching {parallel_company_count} parallel company workers for {route.replace('_', ' ')}."
        )
        summary = f"{summary} {parallel_summary}".strip() if summary else parallel_summary
    if retry_cap_reached and retry_target_route is not None:
        capped_summary = (
            f"Retry cap reached for {retry_target_route.replace('_', ' ')} after "
            f"{settings.max_research_retries} retries. Proceeding with available evidence."
        )
        summary = f"{summary} {capped_summary}".strip() if summary else capped_summary
    return ExecutorNodeOutput(
        next_route=route,
        summary=summary,
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
            "retry_cap_reached": retry_cap_reached,
            "parallel_company_count": parallel_company_count,
            "needs_sandbox": needs_sandbox,
            "sandbox_purpose": sandbox_purpose,
        },
    )


def _count_route_attempts(node_input: ExecutorNodeInput, route: WorkflowRoute) -> int:
    route_to_agent = {
        "planner": "research_planner",
        "company_discovery": "company_discovery",
        "web_research": "web_research",
        "structured_extraction": "structured_extraction",
        "comparison": "comparison",
        "critic_verifier": "critic_verifier",
        "report_generation": "report_generation",
        "chart_generation": "chart_generation",
        "dashboard_builder": "dashboard_builder",
        "session_chatbot": "session_chatbot",
    }
    target_agent = route_to_agent.get(route)
    if target_agent is None:
        return 0
    total_task_runs = sum(1 for task in node_input.state.run.agent_tasks if task.agent_name == target_agent)
    return max(0, total_task_runs - 1)


def _determine_post_retry_route(node_input: ExecutorNodeInput) -> WorkflowRoute:
    state = node_input.state
    if state.report is None or not state.chart_specs:
        return "output_generation"
    if state.dashboard_state is None:
        return "dashboard_builder"
    return "session_chatbot"
