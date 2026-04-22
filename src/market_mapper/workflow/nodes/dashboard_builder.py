"""Dashboard builder workflow node."""

from __future__ import annotations

from market_mapper.agents.dashboard_builder import run_dashboard_builder
from market_mapper.workflow.contracts import DashboardBuilderNodeInput
from market_mapper.workflow.helpers import complete_agent_task, start_agent_task
from market_mapper.workflow.state import ResearchWorkflowState


def dashboard_builder_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """Execute the dashboard builder placeholder and update workflow state."""

    task = start_agent_task(
        state,
        agent_name="dashboard_builder",
        task_type="build_dashboard",
        inputs={
            "report_id": state.report.id,
            "chart_count": len(state.chart_specs),
        },
    )
    node_output = run_dashboard_builder(
        DashboardBuilderNodeInput(
            session_id=state.session.id,
            run_id=state.run.id,
            company_profiles=state.company_profiles,
            comparison_result=state.comparison_result,
            report=state.report,
            chart_specs=state.chart_specs,
            source_documents=state.source_documents,
        )
    )
    state.dashboard_state = node_output.dashboard_state
    state.session.attach_dashboard(state.dashboard_state.id)
    state.run.current_node = "dashboard_builder"
    complete_agent_task(
        state,
        task=task,
        outputs={"dashboard_state_id": state.dashboard_state.id},
        summary=node_output.summary,
    )
    return state
