"""Executor workflow node."""

from __future__ import annotations

from market_mapper.agents.executor import run_workflow_executor
from market_mapper.schemas.models import SandboxTask
from market_mapper.workflow.contracts import ExecutorNodeInput
from market_mapper.workflow.helpers import complete_agent_task, start_agent_task
from market_mapper.workflow.state import ResearchWorkflowState


def _find_retry_task_id(state: ResearchWorkflowState, route_name: str | None) -> str | None:
    if route_name is None:
        return None
    route_to_agent = {
        "planner": "research_planner",
        "company_discovery": "company_discovery",
        "web_research": "web_research",
        "structured_extraction": "structured_extraction",
        "comparison": "comparison",
        "critic_verifier": "critic_verifier",
        "report_generation": "report_generation",
        "chart_generation": "chart_generation",
        "dashboard_builder": "dashboard_builder",
        "session_chatbot": "session_chatbot",
    }
    target_agent = route_to_agent.get(route_name)
    if target_agent is None:
        return None
    for agent_task in reversed(state.run.agent_tasks):
        if agent_task.agent_name == target_agent:
            return agent_task.id
    return None


def _ensure_sandbox_task(
    state: ResearchWorkflowState,
    *,
    route_name: str,
    purpose: str,
    agent_task_id: str,
) -> SandboxTask | None:
    for sandbox_task in reversed(state.sandbox_tasks):
        if (
            sandbox_task.route_name == route_name
            and sandbox_task.status in {"pending", "running", "resumable"}
        ):
            return None

    sandbox_task = SandboxTask(
        run_id=state.run.id,
        route_name=route_name,
        purpose=purpose,
        agent_task_id=agent_task_id,
    )
    state.sandbox_tasks.append(sandbox_task)
    state.run.add_sandbox_task(sandbox_task.id)
    executor_task = state.run.get_task(agent_task_id)
    executor_task.add_sandbox_task(sandbox_task.id)
    return sandbox_task


def executor_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """Coordinate downstream routing, retries, sandbox intent, and checkpoints."""

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
    state.executor_route = node_output.next_route
    state.executor_summary = node_output.summary
    state.run.current_node = "executor"

    if node_output.retry_requested:
        state.run.request_retry(
            node_output.retry_reason or f"Retry requested for route '{node_output.next_route}'.",
            requested_by="workflow_executor",
        )
        retry_task_id = _find_retry_task_id(state, node_output.retry_target_route)
        if retry_task_id is not None:
            retry_task = state.run.get_task(retry_task_id)
            retry_task.request_retry(
                node_output.retry_reason or "Executor requested retry.",
                requested_by="workflow_executor",
            )
            state.run.add_task(retry_task)

    created_sandbox_task = None
    if node_output.needs_sandbox and node_output.sandbox_purpose:
        created_sandbox_task = _ensure_sandbox_task(
            state,
            route_name=node_output.next_route,
            purpose=node_output.sandbox_purpose,
            agent_task_id=task.id,
        )

    state.run.add_checkpoint(
        node_name="executor",
        summary=node_output.summary,
        payload={
            **node_output.checkpoint_payload,
            "created_sandbox_task_id": (
                created_sandbox_task.id if created_sandbox_task is not None else None
            ),
        },
    )
    state.session.status = state.run.status
    complete_agent_task(
        state,
        task=task,
        outputs={
            "next_route": node_output.next_route,
            "retry_requested": node_output.retry_requested,
            "retry_target_route": node_output.retry_target_route,
            "needs_sandbox": node_output.needs_sandbox,
            "sandbox_task_id": (
                created_sandbox_task.id if created_sandbox_task is not None else None
            ),
        },
        summary=node_output.summary,
    )
    return state
