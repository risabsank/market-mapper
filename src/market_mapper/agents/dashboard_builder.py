"""OpenAI-powered Dashboard Builder implementation."""

from __future__ import annotations

from market_mapper.services import generate_structured_output, render_agent_input
from market_mapper.workflow.contracts import (
    DashboardBuilderNodeInput,
    DashboardBuilderNodeOutput,
)

DASHBOARD_SYSTEM_PROMPT = """
You are the Dashboard Builder for Market Mapper.

Turn the approved report, charts, and research outputs into dashboard state.

Rules:
- Create sections that follow a readable flow from summary to evidence.
- Reference report, chart, and source ids when useful.
- Keep the executive summary concise.
"""


def run_dashboard_builder(
    node_input: DashboardBuilderNodeInput,
) -> DashboardBuilderNodeOutput:
    """Create an OpenAI-generated dashboard state from completed outputs."""

    response = generate_structured_output(
        response_model=DashboardBuilderNodeOutput,
        system_prompt=DASHBOARD_SYSTEM_PROMPT,
        user_input=render_agent_input(
            task_description="Build dashboard state from the completed research outputs.",
            context={
                "session_id": node_input.session_id,
                "run_id": node_input.run_id,
                "company_profiles": [
                    profile.model_dump(mode="json")
                    for profile in node_input.company_profiles
                ],
                "comparison_result": node_input.comparison_result.model_dump(mode="json"),
                "report": node_input.report.model_dump(mode="json"),
                "chart_specs": [
                    chart.model_dump(mode="json")
                    for chart in node_input.chart_specs
                ],
                "source_documents": [
                    document.model_dump(mode="json")
                    for document in node_input.source_documents
                ],
            },
        ),
    )
    response.dashboard_state.session_id = node_input.session_id
    response.dashboard_state.run_id = node_input.run_id
    response.next_route = "executor"
    return response

