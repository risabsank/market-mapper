"""Parallel output generation workflow node."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from market_mapper.agents.chart_generation import run_chart_generation
from market_mapper.agents.report_generation import run_report_generation
from market_mapper.workflow.contracts import ChartGenerationNodeInput, ReportGenerationNodeInput
from market_mapper.workflow.helpers import complete_agent_task, execute_sandbox_for_route, start_agent_task
from market_mapper.workflow.nodes.chart_generation import _attach_chart_artifacts
from market_mapper.workflow.nodes.report_generation import _attach_report_artifact
from market_mapper.workflow.state import ResearchWorkflowState


def output_generation_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """Generate report and charts in parallel once research is approved."""

    task = start_agent_task(
        state,
        agent_name="output_generation",
        task_type="generate_outputs_parallel",
        inputs={"comparison_result_id": state.comparison_result.id},
    )

    with ThreadPoolExecutor(max_workers=2, thread_name_prefix=f"market-mapper-output-{state.run.id[:8]}") as executor:
        report_future = executor.submit(
            run_report_generation,
            ReportGenerationNodeInput(
                run_id=state.run.id,
                research_plan=state.session.research_plan,
                company_profiles=state.company_profiles,
                comparison_result=state.comparison_result,
                source_documents=state.source_documents,
            ),
        )
        chart_future = executor.submit(
            run_chart_generation,
            ChartGenerationNodeInput(
                run_id=state.run.id,
                comparison_result=state.comparison_result,
                company_profiles=state.company_profiles,
                existing_chart_specs=state.chart_specs,
                existing_artifacts=state.sandbox_artifacts,
                existing_sandbox_tasks=state.sandbox_tasks,
            ),
        )
        report_output = report_future.result()
        chart_output = chart_future.result()

    execute_sandbox_for_route(
        state,
        route_name="report_generation",
        target_agent_task=task,
        payload=report_output.report.model_dump(mode="json"),
    )
    state.report = _attach_report_artifact(state, report_output.report)

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
                for chart in chart_output.chart_specs
            ],
        },
    )
    state.chart_specs = _attach_chart_artifacts(state, chart_output.chart_specs)
    state.run.current_node = "output_generation"
    complete_agent_task(
        state,
        task=task,
        outputs={
            "report_id": state.report.id if state.report else None,
            "chart_ids": [chart.id for chart in state.chart_specs],
        },
        summary=(
            f"Parallel output generation completed report generation and "
            f"{len(state.chart_specs)} chart artifacts."
        ),
    )
    return state
