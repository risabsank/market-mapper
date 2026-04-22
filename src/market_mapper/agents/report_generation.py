"""OpenAI-powered Report Generation Agent implementation."""

from __future__ import annotations

from market_mapper.services import generate_structured_output, render_agent_input
from market_mapper.workflow.contracts import (
    ReportGenerationNodeInput,
    ReportGenerationNodeOutput,
)

REPORT_SYSTEM_PROMPT = """
You are the Report Generation Agent for Market Mapper.

Create a structured report from the approved comparison state.

Rules:
- Write a clear title and executive summary.
- Create sections that are useful to founders and product teams.
- Keep the markdown_body aligned with the structured sections.
- Cite source document ids where possible.
"""


def run_report_generation(
    node_input: ReportGenerationNodeInput,
) -> ReportGenerationNodeOutput:
    """Create an OpenAI-generated Markdown report from the comparison result."""

    response = generate_structured_output(
        response_model=ReportGenerationNodeOutput,
        system_prompt=REPORT_SYSTEM_PROMPT,
        user_input=render_agent_input(
            task_description="Generate the structured report and markdown export.",
            context={
                "run_id": node_input.run_id,
                "research_plan": node_input.research_plan.model_dump(mode="json"),
                "company_profiles": [
                    profile.model_dump(mode="json")
                    for profile in node_input.company_profiles
                ],
                "comparison_result": node_input.comparison_result.model_dump(mode="json"),
                "source_documents": [
                    document.model_dump(mode="json")
                    for document in node_input.source_documents
                ],
            },
        ),
    )
    response.report.run_id = node_input.run_id
    response.next_route = "executor"
    return response

