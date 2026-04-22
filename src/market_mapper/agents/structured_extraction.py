"""OpenAI-powered Structured Extraction Agent implementation."""

from __future__ import annotations

from market_mapper.services import generate_structured_output, render_agent_input
from market_mapper.workflow.contracts import (
    StructuredExtractionNodeInput,
    StructuredExtractionNodeOutput,
)

STRUCTURED_EXTRACTION_SYSTEM_PROMPT = """
You are the Structured Extraction Agent for Market Mapper.

Turn discovery candidates and source documents into normalized company profiles.

Rules:
- Use source-backed information when possible.
- If a field is unavailable, leave it empty rather than inventing data.
- Keep claims concise and structured.
- Confidence should reflect how grounded the information appears.
"""


def run_structured_extraction(
    node_input: StructuredExtractionNodeInput,
) -> StructuredExtractionNodeOutput:
    """Create OpenAI-generated company profiles from research inputs."""

    response = generate_structured_output(
        response_model=StructuredExtractionNodeOutput,
        system_prompt=STRUCTURED_EXTRACTION_SYSTEM_PROMPT,
        user_input=render_agent_input(
            task_description="Normalize the research inputs into structured company profiles.",
            context={
                "run_id": node_input.run_id,
                "company_candidates": [
                    candidate.model_dump(mode="json")
                    for candidate in node_input.company_candidates
                ],
                "source_documents": [
                    document.model_dump(mode="json")
                    for document in node_input.source_documents
                ],
                "existing_profiles": [
                    profile.model_dump(mode="json")
                    for profile in node_input.existing_profiles
                ],
            },
        ),
    )
    response.next_route = "executor"
    return response

