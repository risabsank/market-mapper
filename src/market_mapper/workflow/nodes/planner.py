"""Planner workflow node."""

from __future__ import annotations

from market_mapper.agents.planner import run_research_planner
from market_mapper.workflow.contracts import PlannerNodeInput
from market_mapper.workflow.helpers import complete_agent_task, start_agent_task
from market_mapper.workflow.state import ResearchWorkflowState


def planner_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """Execute the planner placeholder and update workflow state."""

    task = start_agent_task(
        state,
        agent_name="research_planner",
        task_type="plan_research",
        inputs={"user_prompt": state.session.user_prompt},
    )
    node_output = run_research_planner(
        PlannerNodeInput(
            session_id=state.session.id,
            user_prompt=state.session.user_prompt,
            existing_plan=state.session.research_plan,
        )
    )
    state.session.research_plan = node_output.research_plan
    state.run.current_node = "planner"
    complete_agent_task(
        state,
        task=task,
        outputs={"research_plan_id": node_output.research_plan.id},
        summary=node_output.summary,
    )
    return state
