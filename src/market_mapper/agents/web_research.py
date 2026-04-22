"""OpenAI-powered Web Research Agent implementation."""

from __future__ import annotations

from market_mapper.services import generate_structured_output, render_agent_input
from market_mapper.workflow.contracts import WebResearchNodeInput, WebResearchNodeOutput

WEB_RESEARCH_SYSTEM_PROMPT = """
You are the Web Research Agent for Market Mapper.

Collect source documents that are likely to support downstream extraction and comparison.

Rules:
- Prefer official company websites and product pages.
- Include titles and short snippets when possible.
- Return source documents only; do not summarize the full market yet.
- Use public web knowledge and web search when available.
"""


def run_web_research(node_input: WebResearchNodeInput) -> WebResearchNodeOutput:
    """Return OpenAI-generated source documents for selected companies."""

    response = generate_structured_output(
        response_model=WebResearchNodeOutput,
        system_prompt=WEB_RESEARCH_SYSTEM_PROMPT,
        user_input=render_agent_input(
            task_description="Collect public source documents for the selected companies.",
            context={
                "run_id": node_input.run_id,
                "research_plan": node_input.research_plan.model_dump(mode="json"),
                "company_candidates": [
                    candidate.model_dump(mode="json")
                    for candidate in node_input.company_candidates
                ],
                "existing_documents": [
                    document.model_dump(mode="json")
                    for document in node_input.existing_documents
                ],
            },
        ),
        use_web_search=True,
    )
    response.next_route = "executor"
    return response

