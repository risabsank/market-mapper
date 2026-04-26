"""Web research workflow node."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
from pathlib import Path

from market_mapper.agents.web_research import run_web_research
from market_mapper.schemas.models import AgentTask, CompanyCandidate, SourceDocument
from market_mapper.workflow.contracts import WebResearchNodeInput
from market_mapper.workflow.helpers import (
    complete_agent_task,
    execute_sandbox_for_route,
    persist_workflow_state,
    start_agent_task,
)
from market_mapper.workflow.state import ResearchWorkflowState


def web_research_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """Execute web research planning plus sandbox-backed page capture."""

    task = start_agent_task(
        state,
        agent_name="web_research",
        task_type="collect_sources",
        inputs={"company_candidate_count": len(state.company_candidates)},
    )
    company_outputs: list[tuple[CompanyCandidate, list[SourceDocument], str]] = []
    if state.company_candidates:
        worker_count = min(4, max(1, len(state.company_candidates)))
        child_tasks: dict[str, AgentTask] = {}
        with ThreadPoolExecutor(
            max_workers=worker_count,
            thread_name_prefix=f"market-mapper-research-{state.run.id[:8]}",
        ) as executor:
            future_map = {}
            for candidate in state.company_candidates:
                child_task = _start_company_research_task(state, candidate)
                child_tasks[candidate.id] = child_task
                future = executor.submit(
                    _run_company_web_research,
                    state.run.id,
                    state.session.research_plan,
                    candidate,
                    _filter_documents_for_company(state.source_documents, candidate),
                )
                future_map[future] = candidate

            for future in as_completed(future_map):
                candidate = future_map[future]
                planned_documents, summary = future.result()
                child_task = child_tasks[candidate.id]
                company_outputs.append((candidate, planned_documents, summary))
                state.source_documents = _merge_source_documents(
                    state.source_documents,
                    planned_documents,
                )
                complete_agent_task(
                    state,
                    task=child_task,
                    outputs={
                        "company_candidate_id": candidate.id,
                        "source_document_ids": [document.id for document in planned_documents],
                        "captured_source_count": len(planned_documents),
                    },
                    summary=summary,
                )

    planned_source_documents = _merge_source_documents(
        [],
        [
            document
            for _, documents, _ in company_outputs
            for document in documents
        ],
    )
    execute_sandbox_for_route(
        state,
        route_name="web_research",
        target_agent_task=task,
        payload={
            "research_plan": state.session.research_plan.model_dump(mode="json"),
            "company_candidates": [
                candidate.model_dump(mode="json")
                for candidate in state.company_candidates
            ],
            "existing_documents": [
                document.model_dump(mode="json")
                for document in state.source_documents
            ],
            "source_documents": [
                document.model_dump(mode="json")
                for document in planned_source_documents
            ],
        },
    )
    state.source_documents = _load_captured_source_documents(state) or planned_source_documents
    state.run.current_node = "web_research"
    complete_agent_task(
        state,
        task=task,
        outputs={
            "source_document_ids": [document.id for document in state.source_documents],
            "captured_source_count": len(state.source_documents),
            "parallel_company_count": len(state.company_candidates),
        },
        summary=(
            f"Web research fan-out completed for {len(state.company_candidates)} companies and "
            f"captured {len(state.source_documents)} source documents."
        )
    )
    return state


def _start_company_research_task(
    state: ResearchWorkflowState,
    candidate: CompanyCandidate,
) -> AgentTask:
    task = AgentTask(
        run_id=state.run.id,
        agent_name="web_research",
        task_type="collect_sources_company",
        inputs={
            "company_candidate_id": candidate.id,
            "company_name": candidate.name,
        },
    )
    task.mark_running()
    state.run.add_task(task)
    persist_workflow_state(state)
    return task


def _run_company_web_research(
    run_id: str,
    research_plan,
    candidate: CompanyCandidate,
    existing_documents: list[SourceDocument],
) -> tuple[list[SourceDocument], str]:
    node_output = run_web_research(
        WebResearchNodeInput(
            run_id=run_id,
            research_plan=research_plan,
            company_candidates=[candidate],
            existing_documents=existing_documents,
        )
    )
    return (
        node_output.source_documents,
        f"Collected {len(node_output.source_documents)} planned sources for {candidate.name}.",
    )


def _filter_documents_for_company(
    documents: list[SourceDocument],
    candidate: CompanyCandidate,
) -> list[SourceDocument]:
    candidate_name = candidate.name.strip().lower()
    filtered = [
        document
        for document in documents
        if str(document.metadata.get("company_name", "")).strip().lower() == candidate_name
    ]
    return filtered


def _merge_source_documents(
    existing_documents: list[SourceDocument],
    new_documents: list[SourceDocument],
) -> list[SourceDocument]:
    deduped_by_url = {document.url: document for document in existing_documents if document.url}
    for document in new_documents:
        if document.url:
            deduped_by_url[document.url] = document
    return list(deduped_by_url.values())


def _load_captured_source_documents(state: ResearchWorkflowState) -> list[SourceDocument]:
    artifact_ids_by_path = {
        artifact.path: artifact.id
        for artifact in state.sandbox_artifacts
        if artifact.path
    }
    captured_documents: list[SourceDocument] = []
    for sandbox_task in state.sandbox_tasks:
        if sandbox_task.route_name != "web_research" or not sandbox_task.output_manifest_path:
            continue
        manifest_path = Path(sandbox_task.output_manifest_path)
        if not manifest_path.exists():
            continue
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for document_payload in manifest.get("metadata", {}).get("source_documents", []):
            metadata = dict(document_payload.get("metadata", {}))
            snapshot_path = metadata.get("screenshot_path") or metadata.get("html_path")
            source_document = SourceDocument.model_validate(document_payload)
            if snapshot_path:
                source_document.snapshot_artifact_id = artifact_ids_by_path.get(snapshot_path)
            source_document.metadata = metadata
            captured_documents.append(source_document)
    deduped_by_url = {}
    for document in captured_documents:
        deduped_by_url[document.url] = document
    return list(deduped_by_url.values())
