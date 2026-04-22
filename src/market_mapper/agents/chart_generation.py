"""OpenAI-powered Chart Generation Agent implementation."""

from __future__ import annotations

from market_mapper.charts import build_fallback_chart_specs, validate_chart_specs
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
- Prioritize chart-ready data that compares companies across confidence, source coverage,
  and dimension coverage when useful.
"""


def run_chart_generation(
    node_input: ChartGenerationNodeInput,
) -> ChartGenerationNodeOutput:
    """Create validated chart specs from the comparison result."""

    fallback_specs = build_fallback_chart_specs(
        run_id=node_input.run_id,
        comparison_result=node_input.comparison_result,
        company_profiles=node_input.company_profiles,
    )
    response = generate_structured_output(
        response_model=ChartGenerationNodeOutput,
        system_prompt=CHART_SYSTEM_PROMPT,
        user_input=render_agent_input(
            task_description="Generate chart specs for the dashboard.",
            context={
                "run_id": node_input.run_id,
                "comparison_result": node_input.comparison_result.model_dump(mode="json"),
                "company_profiles": [
                    profile.model_dump(mode="json")
                    for profile in node_input.company_profiles
                ],
                "fallback_chart_specs": [
                    spec.model_dump(mode="json")
                    for spec in fallback_specs
                ],
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
    response.chart_specs = validate_chart_specs(
        chart_specs=response.chart_specs or fallback_specs,
        run_id=node_input.run_id,
        comparison_result=node_input.comparison_result,
    )
    if not response.chart_specs:
        response.chart_specs = validate_chart_specs(
            chart_specs=fallback_specs,
            run_id=node_input.run_id,
            comparison_result=node_input.comparison_result,
        )
    response.summary = f"Chart generation produced {len(response.chart_specs)} validated chart specs."
    response.next_route = "executor"
    response.used_sandbox = True
    return response
