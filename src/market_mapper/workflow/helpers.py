"""Helpers for workflow node execution and task tracking."""

from __future__ import annotations

from market_mapper.schemas.models import AgentTask, SandboxArtifact
from market_mapper.sandbox import SandboxService
from market_mapper.workflow.state import ResearchWorkflowState


def start_agent_task(
    state: ResearchWorkflowState,
    *,
    agent_name: str,
    task_type: str,
    inputs: dict,
) -> AgentTask:
    """Create and attach an agent task to the active run."""

    state.run.mark_running(current_node=task_type)
    task = AgentTask(
        run_id=state.run.id,
        agent_name=agent_name,
        task_type=task_type,
        inputs=inputs,
    )
    task.mark_running()
    state.run.add_task(task)
    state.touch()
    return task


def complete_agent_task(
    state: ResearchWorkflowState,
    *,
    task: AgentTask,
    outputs: dict,
    summary: str,
) -> None:
    """Mark a task complete and persist its outputs on the run."""

    task.mark_completed(outputs=outputs, output_summary=summary)
    state.run.add_task(task)
    state.touch()


def fail_agent_task(
    state: ResearchWorkflowState,
    *,
    task: AgentTask,
    error_message: str,
) -> None:
    """Mark a task failed and update the run state."""

    task.mark_failed(error_message)
    state.run.add_task(task)
    state.run.mark_failed(error_message)
    state.touch()


def execute_sandbox_for_route(
    state: ResearchWorkflowState,
    *,
    route_name: str,
    target_agent_task: AgentTask,
    payload: dict,
) -> list[SandboxArtifact]:
    """Execute pending sandbox tasks for a route and attach emitted artifacts."""

    service = SandboxService()
    artifacts = service.execute_route_tasks(
        state=state,
        route_name=route_name,
        payload=payload,
        target_agent_task_id=target_agent_task.id,
    )
    for sandbox_task in state.sandbox_tasks:
        if sandbox_task.route_name == route_name and sandbox_task.id not in target_agent_task.sandbox_task_ids:
            target_agent_task.add_sandbox_task(sandbox_task.id)
    for artifact in artifacts:
        target_agent_task.add_artifact(artifact.id)
    state.run.add_task(target_agent_task)
    state.touch()
    return artifacts
