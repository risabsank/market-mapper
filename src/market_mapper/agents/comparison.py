"""OpenAI-powered Comparison Agent implementation."""

from __future__ import annotations

from market_mapper.services import generate_structured_output, render_agent_input
from market_mapper.workflow.contracts import ComparisonNodeInput, ComparisonNodeOutput

COMPARISON_SYSTEM_PROMPT = """
You are the Comparison Agent for Market Mapper.

Compare the normalized company profiles across the requested dimensions.

Rules:
- Produce structured findings for each dimension.
- Summaries should be concise and decision-useful.
- Do not claim certainty when data is weak.
"""


def run_comparison(node_input: ComparisonNodeInput) -> ComparisonNodeOutput:
    """Generate an OpenAI comparison result from company profiles."""

    response = generate_structured_output(
        response_model=ComparisonNodeOutput,
        system_prompt=COMPARISON_SYSTEM_PROMPT,
        user_input=render_agent_input(
            task_description="Compare the company profiles according to the research plan.",
            context={
                "run_id": node_input.run_id,
                "research_plan": node_input.research_plan.model_dump(mode="json"),
                "company_profiles": [
                    profile.model_dump(mode="json")
                    for profile in node_input.company_profiles
                ],
            },
        ),
    )
    response.comparison_result.run_id = node_input.run_id
    response.next_route = "executor"
    return response

