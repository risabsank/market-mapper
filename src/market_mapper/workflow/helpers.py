"""Helpers for workflow node execution and task tracking."""

from __future__ import annotations

import logging
from collections import defaultdict

from market_mapper.config.settings import get_settings
from market_mapper.schemas.models import (
    AgentTask,
    CompanyWorkspaceStatus,
    SandboxArtifact,
    WorkspaceSectionStatus,
    WorkspaceSnapshot,
)
from market_mapper.schemas.models.common import RunStatus, TaskStatus
from market_mapper.sandbox.service import SandboxService
from market_mapper.storage import FileWorkflowStateStore
from market_mapper.workflow.state import ResearchWorkflowState

logger = logging.getLogger("market_mapper.workflow")


def persist_workflow_state(state: ResearchWorkflowState) -> None:
    """Persist the current workflow state so progress is externally visible."""

    store = FileWorkflowStateStore(get_settings().workflow_state_dir)
    state.workspace_snapshot = build_workspace_snapshot(state)
    store.save_session(state.session)
    store.save_run(state.run)
    store.save_workspace_snapshot(state.workspace_snapshot)
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


def build_workspace_snapshot(state: ResearchWorkflowState) -> WorkspaceSnapshot:
    """Create a progressive dashboard/workspace snapshot from the current workflow state."""

    completed_tasks = sum(1 for task in state.run.agent_tasks if task.status == TaskStatus.COMPLETED)
    total_tasks = max(len(state.run.agent_tasks), 1)
    percent_complete = 100.0 if state.run.status == RunStatus.COMPLETED else round(
        (completed_tasks / total_tasks) * 100.0,
        1,
    )
    source_ids_by_company = defaultdict(list)
    for document in state.source_documents:
        company_name = str(document.metadata.get("company_name", "")).strip().lower()
        if company_name:
            source_ids_by_company[company_name].append(document.id)
    profiles_by_name = {profile.name.strip().lower(): profile for profile in state.company_profiles}

    company_statuses: list[CompanyWorkspaceStatus] = []
    for candidate in state.company_candidates:
        company_key = candidate.name.strip().lower()
        profile = profiles_by_name.get(company_key)
        source_ids = list(dict.fromkeys(source_ids_by_company.get(company_key, [])))
        if profile is not None:
            status = "complete" if state.comparison_result is not None else "running"
            summary = profile.product_summary or profile.positioning_statement or candidate.rationale
            confidence = profile.confidence
            missing_fields = profile.explicit_missing_fields
        elif source_ids:
            status = "running"
            summary = candidate.rationale
            confidence = None
            missing_fields = []
        else:
            status = "pending"
            summary = candidate.rationale
            confidence = None
            missing_fields = []
        company_statuses.append(
            CompanyWorkspaceStatus(
                company_candidate_id=candidate.id,
                company_profile_id=profile.id if profile is not None else None,
                name=candidate.name,
                website=candidate.website,
                status=status,
                summary=summary,
                source_document_ids=source_ids if source_ids else (profile.source_document_ids if profile else []),
                confidence=confidence,
                missing_fields=missing_fields,
            )
        )

    sections = _build_workspace_sections(state, percent_complete)
    return WorkspaceSnapshot(
        session_id=state.session.id,
        user_id=state.session.user_id,
        run_id=state.run.id,
        session_status=state.session.status,
        prompt=state.session.user_prompt,
        research_plan=state.session.research_plan,
        current_node=state.run.current_node,
        completed_tasks=completed_tasks,
        total_tasks=total_tasks,
        percent_complete=percent_complete,
        company_statuses=company_statuses,
        source_documents=state.source_documents,
        company_profiles=state.company_profiles,
        comparison_result=state.comparison_result,
        report=state.report,
        chart_count=len(state.chart_specs),
        dashboard_ready=state.dashboard_state is not None,
        sections=sections,
    )


def _build_workspace_sections(
    state: ResearchWorkflowState,
    percent_complete: float,
) -> list[WorkspaceSectionStatus]:
    steps = [
        (
            "plan",
            "Research Plan",
            state.session.research_plan is not None,
            "Planner turned the prompt into a structured plan.",
        ),
        (
            "discovery",
            "Company Discovery",
            bool(state.company_candidates),
            f"{len(state.company_candidates)} companies are in the working set."
            if state.company_candidates
            else "Waiting for discovery candidates.",
        ),
        (
            "research",
            "Source Collection",
            bool(state.source_documents),
            f"{len(state.source_documents)} source documents have been gathered."
            if state.source_documents
            else "Collecting public sources for each company.",
        ),
        (
            "extraction",
            "Structured Extraction",
            bool(state.company_profiles),
            f"{len(state.company_profiles)} company profiles have been normalized."
            if state.company_profiles
            else "Turning source material into company profiles.",
        ),
        (
            "comparison",
            "Comparison",
            state.comparison_result is not None,
            "Cross-company comparison is ready."
            if state.comparison_result is not None
            else "Waiting for enough structured profiles to compare companies.",
        ),
        (
            "report",
            "Report",
            state.report is not None,
            "Markdown report is available."
            if state.report is not None
            else "Report will generate after comparison is stable.",
        ),
        (
            "charts",
            "Charts",
            bool(state.chart_specs),
            f"{len(state.chart_specs)} chart artifacts are ready."
            if state.chart_specs
            else "Charts will render after comparison is approved.",
        ),
        (
            "dashboard",
            "Dashboard",
            state.dashboard_state is not None,
            "Approved dashboard state is ready."
            if state.dashboard_state is not None
            else "Waiting for approved dashboard assembly.",
        ),
    ]

    sections: list[WorkspaceSectionStatus] = []
    current_node = state.run.current_node or ""
    for key, title, is_complete, summary in steps:
        status = "complete" if is_complete else "pending"
        if not is_complete and current_node and key in current_node:
            status = "running"
        elif not is_complete and current_node in {"web_research", "collect_sources"} and key == "research":
            status = "running"
        elif not is_complete and current_node == "extract_company_profiles" and key == "extraction":
            status = "running"
        progress = 100.0 if is_complete else percent_complete
        sections.append(
            WorkspaceSectionStatus(
                key=key,
                title=title,
                status=status,
                summary=summary,
                progress_percent=progress,
            )
        )
    return sections
