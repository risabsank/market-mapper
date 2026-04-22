"""Executor workflow node."""

from __future__ import annotations

from market_mapper.agents.executor import run_workflow_executor
from market_mapper.workflow.contracts import ExecutorNodeInput
from market_mapper.workflow.helpers import complete_agent_task, start_agent_task
from market_mapper.workflow.state import ResearchWorkflowState


def executor_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """Execute the executor placeholder and update workflow state."""

    task = start_agent_task(
        state,
        agent_name="workflow_executor",
        task_type="route_workflow",
        inputs={"current_node": state.run.current_node or "start"},
    )
    node_output = run_workflow_executor(
        ExecutorNodeInput(
            state=state,
            current_node=state.run.current_node or "start",
        )
    )
    state.run.current_node = "executor"
    state.run.add_checkpoint(
        node_name="executor",
        summary=node_output.summary,
        payload={"next_route": node_output.next_route},
    )
    complete_agent_task(
        state,
        task=task,
        outputs={"next_route": node_output.next_route},
        summary=node_output.summary,
    )
    return state
