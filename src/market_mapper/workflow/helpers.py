"""Helpers for workflow node execution and task tracking."""

from __future__ import annotations

import logging

from market_mapper.config.settings import get_settings
from market_mapper.schemas.models import AgentTask, SandboxArtifact
from market_mapper.sandbox.service import SandboxService
from market_mapper.storage import FileWorkflowStateStore
from market_mapper.workflow.state import ResearchWorkflowState

logger = logging.getLogger("market_mapper.workflow")


def persist_workflow_state(state: ResearchWorkflowState) -> None:
    """Persist the current workflow state so progress is externally visible."""

    store = FileWorkflowStateStore(get_settings().workflow_state_dir)
    store.save_session(state.session)
    store.save_run(state.run)
    if state.dashboard_state is not None:
        store.save_dashboard_state(state.dashboard_state)
    for sandbox_task in state.sandbox_tasks:
        store.save_sandbox_task(sandbox_task)
    for artifact in state.sandbox_artifacts:
        store.save_artifact(artifact)


def persist_failed_workflow_state(
    state: ResearchWorkflowState,
    *,
    current_node: str,
    error_message: str,
) -> None:
    """Persist a workflow failure that happened outside a task completion path."""

    state.run.mark_failed(error_message, current_node=current_node)
    state.session.status = state.run.status
    state.touch()
    logger.exception(
        "Run %s failed while executing workflow node %s: %s",
        state.run.id,
        current_node,
        error_message,
    )
    persist_workflow_state(state)


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
    logger.info(
        "Run %s started agent task %s (%s).",
        state.run.id,
        task.agent_name,
        task.task_type,
    )
    persist_workflow_state(state)
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
    logger.info(
        "Run %s completed agent task %s (%s).",
        state.run.id,
        task.agent_name,
        task.task_type,
    )
    persist_workflow_state(state)


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
    logger.error(
        "Run %s failed agent task %s (%s): %s",
        state.run.id,
        task.agent_name,
        task.task_type,
        error_message,
    )
    persist_workflow_state(state)


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
    logger.info(
        "Run %s executed sandbox route %s and attached %s artifacts.",
        state.run.id,
        route_name,
        len(artifacts),
    )
    persist_workflow_state(state)
    return artifacts
