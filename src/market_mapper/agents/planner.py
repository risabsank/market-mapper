"""Research Planner placeholder implementation."""

from __future__ import annotations

from market_mapper.schemas.models import ResearchPlan
from market_mapper.workflow.contracts import PlannerNodeInput, PlannerNodeOutput


def run_research_planner(node_input: PlannerNodeInput) -> PlannerNodeOutput:
    """Build a deterministic placeholder research plan from the user prompt."""

    prompt = node_input.user_prompt.strip()
    plan = node_input.existing_plan or ResearchPlan(
        market_query=prompt,
        requested_company_count=4,
        discovery_criteria=[
            "market relevance",
            "public visibility",
            "official website quality",
        ],
        comparison_dimensions=[
            "pricing",
            "features",
            "positioning",
            "target_customers",
        ],
        assumptions=[
            "Use public web sources only.",
            "Prefer official company sources when available.",
        ],
    )
    plan.touch()

    return PlannerNodeOutput(
        research_plan=plan,
        summary="Research plan prepared by the planner placeholder.",
        assumptions=plan.assumptions,
        next_route="executor",
    )
