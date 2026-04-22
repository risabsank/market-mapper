"""Chart generation workflow node."""

from __future__ import annotations

from market_mapper.agents.chart_generation import run_chart_generation
from market_mapper.workflow.contracts import ChartGenerationNodeInput
from market_mapper.workflow.helpers import (
    complete_agent_task,
    execute_sandbox_for_route,
    start_agent_task,
)
from market_mapper.workflow.state import ResearchWorkflowState


def chart_generation_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """Execute the chart generation placeholder and update workflow state."""

    task = start_agent_task(
        state,
        agent_name="chart_generation",
        task_type="generate_charts",
        inputs={"comparison_result_id": state.comparison_result.id},
    )
    node_output = run_chart_generation(
        ChartGenerationNodeInput(
            run_id=state.run.id,
            comparison_result=state.comparison_result,
            existing_chart_specs=state.chart_specs,
            existing_artifacts=state.sandbox_artifacts,
            existing_sandbox_tasks=state.sandbox_tasks,
        )
    )
    execute_sandbox_for_route(
        state,
        route_name="chart_generation",
        target_agent_task=task,
        payload={
            "comparison_result": state.comparison_result.model_dump(mode="json"),
            "chart_specs": [
                chart.model_dump(mode="json")
                for chart in node_output.chart_specs
            ],
        },
    )
    state.chart_specs = node_output.chart_specs
    state.run.current_node = "chart_generation"
    complete_agent_task(
        state,
        task=task,
        outputs={"chart_ids": [chart.id for chart in state.chart_specs]},
        summary=node_output.summary,
    )
    return state
