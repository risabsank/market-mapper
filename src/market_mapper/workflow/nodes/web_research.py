"""Web research workflow node."""

from __future__ import annotations

from market_mapper.agents.web_research import run_web_research
from market_mapper.workflow.contracts import WebResearchNodeInput
from market_mapper.workflow.helpers import complete_agent_task, start_agent_task
from market_mapper.workflow.state import ResearchWorkflowState


def web_research_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """Execute the web research placeholder and update workflow state."""

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
    state.source_documents = node_output.source_documents
    state.run.current_node = "web_research"
    complete_agent_task(
        state,
        task=task,
        outputs={"source_document_ids": [document.id for document in state.source_documents]},
        summary=node_output.summary,
    )
    return state
