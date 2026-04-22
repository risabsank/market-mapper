"""OpenAI-powered Chart Generation Agent implementation."""

from __future__ import annotations

from market_mapper.services import generate_structured_output, render_agent_input
from market_mapper.workflow.contracts import (
    ChartGenerationNodeInput,
    ChartGenerationNodeOutput,
)

CHART_SYSTEM_PROMPT = """
You are the Chart Generation Agent for Market Mapper.

Produce chart specs that the dashboard can render.

Rules:
- Return useful chart specs only when the comparison data supports them.
- Prefer simple chart types like bar, grouped_bar, heatmap, or scorecard.
- Keep chart data compact and aligned to the supplied comparison result.
"""


def run_chart_generation(
    node_input: ChartGenerationNodeInput,
) -> ChartGenerationNodeOutput:
    """Create OpenAI-generated chart specs from the comparison result."""

    response = generate_structured_output(
        response_model=ChartGenerationNodeOutput,
        system_prompt=CHART_SYSTEM_PROMPT,
        user_input=render_agent_input(
            task_description="Generate chart specs for the dashboard.",
            context={
                "run_id": node_input.run_id,
                "comparison_result": node_input.comparison_result.model_dump(mode="json"),
                "existing_chart_specs": [
                    spec.model_dump(mode="json")
                    for spec in node_input.existing_chart_specs
                ],
                "existing_artifacts": [
                    artifact.model_dump(mode="json")
                    for artifact in node_input.existing_artifacts
                ],
                "existing_sandbox_tasks": [
                    task.model_dump(mode="json")
                    for task in node_input.existing_sandbox_tasks
                ],
            },
        ),
    )
    for chart_spec in response.chart_specs:
        chart_spec.run_id = node_input.run_id
    response.next_route = "executor"
    response.used_sandbox = True
    return response

