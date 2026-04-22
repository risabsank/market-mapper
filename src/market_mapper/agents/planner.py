"""OpenAI-powered Research Planner implementation."""

from __future__ import annotations

from market_mapper.schemas.models import ResearchPlan
from market_mapper.services import generate_structured_output, render_agent_input
from market_mapper.workflow.contracts import PlannerNodeInput, PlannerNodeOutput

PLANNER_SYSTEM_PROMPT = """
You are the Research Planner for Market Mapper.

Turn the user's research request into a structured research plan.

Rules:
- Produce a market_query that captures the actual market or company set to study.
- requested_company_count must be between 1 and 10. Default to 4 when unspecified.
- Fill discovery_criteria with the criteria the downstream discovery agent should use.
- Fill comparison_dimensions with useful dimensions implied by the prompt. Include practical business dimensions such as pricing, features, positioning, target_customers, integrations, ai_capabilities, or proof_points when relevant.
- Record explicit assumptions when the prompt is ambiguous.
- Prefer concise, operational wording over long prose.
- The project uses public sources only, so assumptions should reflect that.
"""


def run_research_planner(node_input: PlannerNodeInput) -> PlannerNodeOutput:
    """Turn a user prompt into a structured research plan with OpenAI."""

    plan = generate_structured_output(
        response_model=ResearchPlan,
        system_prompt=PLANNER_SYSTEM_PROMPT,
        user_input=render_agent_input(
            task_description="Create the research plan for this user request.",
            context={
                "session_id": node_input.session_id,
                "user_prompt": node_input.user_prompt,
                "existing_plan": (
                    node_input.existing_plan.model_dump(mode="json")
                    if node_input.existing_plan
                    else None
                ),
            },
        ),
    )
    if node_input.existing_plan is not None:
        plan.id = node_input.existing_plan.id
        plan.created_at = node_input.existing_plan.created_at
    plan.touch()

    return PlannerNodeOutput(
        research_plan=plan,
        summary=(
            "OpenAI research planner produced a structured plan with "
            f"{plan.requested_company_count} target companies and "
            f"{len(plan.comparison_dimensions)} comparison dimensions."
        ),
        assumptions=plan.assumptions,
        next_route="executor",
    )

