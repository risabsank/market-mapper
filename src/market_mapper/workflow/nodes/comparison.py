"""Comparison workflow node."""

from __future__ import annotations

from market_mapper.agents.comparison import run_comparison
from market_mapper.workflow.contracts import ComparisonNodeInput
from market_mapper.workflow.helpers import complete_agent_task, start_agent_task
from market_mapper.workflow.state import ResearchWorkflowState


def comparison_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """Execute the comparison placeholder and update workflow state."""

    task = start_agent_task(
        state,
        agent_name="comparison",
        task_type="compare_companies",
        inputs={"company_profile_count": len(state.company_profiles)},
    )
    node_output = run_comparison(
        ComparisonNodeInput(
            run_id=state.run.id,
            research_plan=state.session.research_plan,
            company_profiles=state.company_profiles,
        )
    )
    state.comparison_result = node_output.comparison_result
    state.run.current_node = "comparison"
    complete_agent_task(
        state,
        task=task,
        outputs={"comparison_result_id": state.comparison_result.id},
        summary=node_output.summary,
    )
    return state
