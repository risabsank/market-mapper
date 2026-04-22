"""Company discovery workflow node."""

from __future__ import annotations

from market_mapper.agents.company_discovery import run_company_discovery
from market_mapper.workflow.contracts import CompanyDiscoveryNodeInput
from market_mapper.workflow.helpers import complete_agent_task, start_agent_task
from market_mapper.workflow.state import ResearchWorkflowState


def company_discovery_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """Execute the company discovery placeholder and update workflow state."""

    task = start_agent_task(
        state,
        agent_name="company_discovery",
        task_type="discover_companies",
        inputs={"research_plan_id": state.session.research_plan.id},
    )
    node_output = run_company_discovery(
        CompanyDiscoveryNodeInput(
            run_id=state.run.id,
            research_plan=state.session.research_plan,
            existing_candidates=state.company_candidates,
        )
    )
    state.company_candidates = node_output.company_candidates
    state.run.current_node = "company_discovery"
    complete_agent_task(
        state,
        task=task,
        outputs={"company_candidate_ids": [candidate.id for candidate in state.company_candidates]},
        summary=node_output.summary,
    )
    return state
