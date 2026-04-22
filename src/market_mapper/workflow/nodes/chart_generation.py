"""Chart generation workflow node."""

from __future__ import annotations

import json
from pathlib import Path

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
            company_profiles=state.company_profiles,
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
            "company_profiles": [
                profile.model_dump(mode="json")
                for profile in state.company_profiles
            ],
            "chart_specs": [
                chart.model_dump(mode="json")
                for chart in node_output.chart_specs
            ],
        },
    )
    state.chart_specs = _attach_chart_artifacts(state, node_output.chart_specs)
    state.run.current_node = "chart_generation"
    complete_agent_task(
        state,
        task=task,
        outputs={"chart_ids": [chart.id for chart in state.chart_specs]},
        summary=node_output.summary,
    )
    return state


def _attach_chart_artifacts(state: ResearchWorkflowState, chart_specs):
    artifact_ids_by_chart_id = {}
    for artifact in state.sandbox_artifacts:
        chart_id = artifact.metadata.get("chart_id")
        if chart_id:
            artifact_ids_by_chart_id[chart_id] = artifact.id

    manifest_chart_ids = {}
    for sandbox_task in state.sandbox_tasks:
        if sandbox_task.route_name != "chart_generation" or not sandbox_task.output_manifest_path:
            continue
        manifest_path = Path(sandbox_task.output_manifest_path)
        if not manifest_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for item in manifest.get("metadata", {}).get("rendered_charts", []):
            if item.get("chart_id") and item.get("artifact_path"):
                for artifact in state.sandbox_artifacts:
                    if artifact.path == item["artifact_path"]:
                        manifest_chart_ids[item["chart_id"]] = artifact.id
                        break

    for chart_spec in chart_specs:
        chart_spec.artifact_id = artifact_ids_by_chart_id.get(chart_spec.id) or manifest_chart_ids.get(chart_spec.id)
    return chart_specs
