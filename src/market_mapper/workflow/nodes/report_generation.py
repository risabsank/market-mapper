"""Report generation workflow node."""

from __future__ import annotations

from market_mapper.agents.report_generation import run_report_generation
from market_mapper.workflow.contracts import ReportGenerationNodeInput
from market_mapper.workflow.helpers import complete_agent_task, start_agent_task
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
    state.report = node_output.report
    state.run.current_node = "report_generation"
    complete_agent_task(
        state,
        task=task,
        outputs={"report_id": state.report.id},
        summary=node_output.summary,
    )
    return state
