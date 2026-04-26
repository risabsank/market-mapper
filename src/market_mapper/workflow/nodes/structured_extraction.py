"""Structured extraction workflow node."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed

from market_mapper.agents.structured_extraction import run_structured_extraction
from market_mapper.schemas.models import AgentTask, CompanyCandidate, CompanyProfile, SourceDocument
from market_mapper.workflow.contracts import StructuredExtractionNodeInput
from market_mapper.workflow.helpers import (
    complete_agent_task,
    execute_sandbox_for_route,
    persist_workflow_state,
    start_agent_task,
)
from market_mapper.workflow.state import ResearchWorkflowState


def structured_extraction_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """Execute the structured extraction placeholder and update workflow state."""

    task = start_agent_task(
        state,
        agent_name="structured_extraction",
        task_type="extract_company_profiles",
        inputs={"source_document_count": len(state.source_documents)},
    )
    company_profiles: list[CompanyProfile] = []
    if state.company_candidates:
        worker_count = min(4, max(1, len(state.company_candidates)))
        child_tasks: dict[str, AgentTask] = {}
        with ThreadPoolExecutor(
            max_workers=worker_count,
            thread_name_prefix=f"market-mapper-extract-{state.run.id[:8]}",
        ) as executor:
            future_map = {}
            for candidate in state.company_candidates:
                child_task = _start_company_extraction_task(state, candidate)
                child_tasks[candidate.id] = child_task
                future = executor.submit(
                    _run_company_extraction,
                    state.run.id,
                    candidate,
                    _filter_documents_for_company(state.source_documents, candidate),
                    _filter_profiles_for_company(state.company_profiles, candidate),
                )
                future_map[future] = candidate

            for future in as_completed(future_map):
                candidate = future_map[future]
                extracted_profiles, summary = future.result()
                child_task = child_tasks[candidate.id]
                company_profiles = _merge_company_profiles(company_profiles, extracted_profiles)
                state.company_profiles = _merge_company_profiles(state.company_profiles, extracted_profiles)
                complete_agent_task(
                    state,
                    task=child_task,
                    outputs={
                        "company_candidate_id": candidate.id,
                        "company_profile_ids": [profile.id for profile in extracted_profiles],
                    },
                    summary=summary,
                )

    execute_sandbox_for_route(
        state,
        route_name="structured_extraction",
        target_agent_task=task,
        payload={
            "company_candidates": [
                candidate.model_dump(mode="json")
                for candidate in state.company_candidates
            ],
            "source_documents": [
                document.model_dump(mode="json")
                for document in state.source_documents
            ],
            "company_profiles": [
                profile.model_dump(mode="json")
                for profile in company_profiles
            ],
        },
    )
    state.company_profiles = company_profiles
    state.run.current_node = "structured_extraction"
    complete_agent_task(
        state,
        task=task,
        outputs={
            "company_profile_ids": [profile.id for profile in state.company_profiles],
            "parallel_company_count": len(state.company_candidates),
        },
        summary=(
            f"Structured extraction fan-out completed for {len(state.company_candidates)} companies and "
            f"produced {len(state.company_profiles)} company profiles."
        )
    )
    return state


def _start_company_extraction_task(
    state: ResearchWorkflowState,
    candidate: CompanyCandidate,
) -> AgentTask:
    task = AgentTask(
        run_id=state.run.id,
        agent_name="structured_extraction",
        task_type="extract_company_profile",
        inputs={
            "company_candidate_id": candidate.id,
            "company_name": candidate.name,
        },
    )
    task.mark_running()
    state.run.add_task(task)
    persist_workflow_state(state)
    return task


def _run_company_extraction(
    run_id: str,
    candidate: CompanyCandidate,
    source_documents: list[SourceDocument],
    existing_profiles: list[CompanyProfile],
) -> tuple[list[CompanyProfile], str]:
    node_output = run_structured_extraction(
        StructuredExtractionNodeInput(
            run_id=run_id,
            company_candidates=[candidate],
            source_documents=source_documents,
            existing_profiles=existing_profiles,
        )
    )
    return (
        node_output.company_profiles,
        f"Structured extraction completed for {candidate.name}.",
    )


def _filter_documents_for_company(
    documents: list[SourceDocument],
    candidate: CompanyCandidate,
) -> list[SourceDocument]:
    candidate_name = candidate.name.strip().lower()
    return [
        document
        for document in documents
        if str(document.metadata.get("company_name", "")).strip().lower() == candidate_name
    ]


def _filter_profiles_for_company(
    profiles: list[CompanyProfile],
    candidate: CompanyCandidate,
) -> list[CompanyProfile]:
    candidate_name = candidate.name.strip().lower()
    return [profile for profile in profiles if profile.name.strip().lower() == candidate_name]


def _merge_company_profiles(
    existing_profiles: list[CompanyProfile],
    new_profiles: list[CompanyProfile],
) -> list[CompanyProfile]:
    deduped_by_name = {profile.name.strip().lower(): profile for profile in existing_profiles}
    for profile in new_profiles:
        deduped_by_name[profile.name.strip().lower()] = profile
    return list(deduped_by_name.values())
