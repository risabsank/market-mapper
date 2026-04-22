"""Report generation workflow node."""

from __future__ import annotations

import json
from pathlib import Path

from market_mapper.agents.report_generation import run_report_generation
from market_mapper.workflow.contracts import ReportGenerationNodeInput
from market_mapper.workflow.helpers import (
    complete_agent_task,
    execute_sandbox_for_route,
    start_agent_task,
)
from market_mapper.workflow.state import ResearchWorkflowState


def report_generation_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """Execute the report generation placeholder and update workflow state."""

    task = start_agent_task(
        state,
        agent_name="report_generation",
        task_type="generate_report",
        inputs={"comparison_result_id": state.comparison_result.id},
    )
    node_output = run_report_generation(
        ReportGenerationNodeInput(
            run_id=state.run.id,
            research_plan=state.session.research_plan,
            company_profiles=state.company_profiles,
            comparison_result=state.comparison_result,
            source_documents=state.source_documents,
        )
    )
    execute_sandbox_for_route(
        state,
        route_name="report_generation",
        target_agent_task=task,
        payload=node_output.report.model_dump(mode="json"),
    )
    state.report = _attach_report_artifact(state, node_output.report)
    state.run.current_node = "report_generation"
    complete_agent_task(
        state,
        task=task,
        outputs={
            "report_id": state.report.id,
            "report_artifact_id": state.report.artifact_id,
        },
        summary=node_output.summary,
    )
    return state


def _attach_report_artifact(state: ResearchWorkflowState, report):
    artifact_id = None
    for artifact in state.sandbox_artifacts:
        if artifact.metadata.get("report_id") == report.id and artifact.kind == "markdown_report":
            artifact_id = artifact.id
            break

    if artifact_id is None:
        for sandbox_task in state.sandbox_tasks:
            if sandbox_task.route_name != "report_generation" or not sandbox_task.output_manifest_path:
                continue
            manifest_path = Path(sandbox_task.output_manifest_path)
            if not manifest_path.exists():
                continue
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            report_id = manifest.get("metadata", {}).get("report_id")
            if report_id != report.id:
                continue
            artifact_paths = set(manifest.get("metadata", {}).get("artifact_paths", []))
            for artifact in state.sandbox_artifacts:
                if artifact.path in artifact_paths and artifact.kind == "markdown_report":
                    artifact_id = artifact.id
                    break
            if artifact_id:
                break

    report.artifact_id = artifact_id
    return report
