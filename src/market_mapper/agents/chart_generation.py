"""Chart Generation Agent placeholder implementation."""

from __future__ import annotations

from market_mapper.schemas.models import ChartSpec
from market_mapper.workflow.contracts import (
    ChartGenerationNodeInput,
    ChartGenerationNodeOutput,
)


def run_chart_generation(
    node_input: ChartGenerationNodeInput,
) -> ChartGenerationNodeOutput:
    """Create placeholder chart specs from the comparison result."""

    chart_specs = node_input.existing_chart_specs or [
        ChartSpec(
            run_id=node_input.run_id,
            chart_type="bar",
            title="Placeholder Comparison Chart",
            description="Chart skeleton generated before real chart rendering exists.",
            data=[
                {"company_id": company_id, "value": index + 1}
                for index, company_id in enumerate(node_input.comparison_result.company_ids)
            ],
            x_field="company_id",
            y_field="value",
            comparison_result_id=node_input.comparison_result.id,
        )
    ]
    return ChartGenerationNodeOutput(
        chart_specs=chart_specs,
        used_sandbox=True,
        summary="Chart generation placeholder created chart specs.",
        next_route="executor",
    )
