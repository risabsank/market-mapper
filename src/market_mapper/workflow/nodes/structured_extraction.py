"""Structured extraction workflow node."""

from __future__ import annotations

from market_mapper.agents.structured_extraction import run_structured_extraction
from market_mapper.workflow.contracts import StructuredExtractionNodeInput
from market_mapper.workflow.helpers import complete_agent_task, start_agent_task
from market_mapper.workflow.state import ResearchWorkflowState


def structured_extraction_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """Execute the structured extraction placeholder and update workflow state."""

    task = start_agent_task(
        state,
        agent_name="structured_extraction",
        task_type="extract_company_profiles",
        inputs={"source_document_count": len(state.source_documents)},
    )
    node_output = run_structured_extraction(
        StructuredExtractionNodeInput(
            run_id=state.run.id,
            company_candidates=state.company_candidates,
            source_documents=state.source_documents,
            existing_profiles=state.company_profiles,
        )
    )
    state.company_profiles = node_output.company_profiles
    state.run.current_node = "structured_extraction"
    complete_agent_task(
        state,
        task=task,
        outputs={"company_profile_ids": [profile.id for profile in state.company_profiles]},
        summary=node_output.summary,
    )
    return state
