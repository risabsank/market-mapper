"""OpenAI-powered Company Discovery Agent implementation."""

from __future__ import annotations

from market_mapper.services import generate_structured_output, render_agent_input
from market_mapper.workflow.contracts import (
    CompanyDiscoveryNodeInput,
    CompanyDiscoveryNodeOutput,
)

DISCOVERY_SYSTEM_PROMPT = """
You are the Company Discovery Agent for Market Mapper.

Identify candidate companies that match the research plan.

Rules:
- Return 3 to 5 candidates unless the requested company count is lower.
- Favor companies that fit the research plan's market query and discovery criteria.
- Include rationale and a relevance score for each candidate.
- Use public information and web knowledge. When web search is available, use it.
- Do not invent exact private metrics.
"""


def run_company_discovery(
    node_input: CompanyDiscoveryNodeInput,
) -> CompanyDiscoveryNodeOutput:
    """Return OpenAI-generated company candidates from the research plan."""

    response = generate_structured_output(
        response_model=CompanyDiscoveryNodeOutput,
        system_prompt=DISCOVERY_SYSTEM_PROMPT,
        user_input=render_agent_input(
            task_description="Discover candidate companies for this market research plan.",
            context={
                "run_id": node_input.run_id,
                "research_plan": node_input.research_plan.model_dump(mode="json"),
                "existing_candidates": [
                    candidate.model_dump(mode="json")
                    for candidate in node_input.existing_candidates
                ],
            },
        ),
        use_web_search=True,
    )
    response.next_route = "executor"
    return response

