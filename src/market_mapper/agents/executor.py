"""Workflow Executor placeholder implementation."""

from __future__ import annotations

from market_mapper.workflow.contracts import ExecutorNodeInput, ExecutorNodeOutput
from market_mapper.workflow.routing import determine_next_route


def run_workflow_executor(node_input: ExecutorNodeInput) -> ExecutorNodeOutput:
    """Choose the next workflow node based on the current state."""

    route = determine_next_route(node_input.state)
    return ExecutorNodeOutput(
        next_route=route,
        summary=f"Executor selected the '{route}' route.",
        current_node=node_input.current_node,
    )
