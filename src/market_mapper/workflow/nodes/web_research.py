"""Web research workflow node."""

from __future__ import annotations

import json
from pathlib import Path

from market_mapper.agents.web_research import run_web_research
from market_mapper.schemas.models import SourceDocument
from market_mapper.workflow.contracts import WebResearchNodeInput
from market_mapper.workflow.helpers import (
    complete_agent_task,
    execute_sandbox_for_route,
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
    node_output = run_web_research(
        WebResearchNodeInput(
            run_id=state.run.id,
            research_plan=state.session.research_plan,
            company_candidates=state.company_candidates,
            existing_documents=state.source_documents,
        )
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
                for document in node_output.source_documents
            ],
        },
    )
    state.source_documents = _load_captured_source_documents(state) or node_output.source_documents
    state.run.current_node = "web_research"
    complete_agent_task(
        state,
        task=task,
        outputs={
            "source_document_ids": [document.id for document in state.source_documents],
            "captured_source_count": len(state.source_documents),
        },
        summary=(
            f"Web research captured {len(state.source_documents)} source documents for extraction."
        ),
    )
    return state


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
