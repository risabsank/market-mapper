"""Critic/verifier workflow node."""

from __future__ import annotations

from market_mapper.agents.critic_verifier import run_critic_verifier
from market_mapper.workflow.contracts import CriticVerifierNodeInput
from market_mapper.workflow.helpers import (
    complete_agent_task,
    execute_sandbox_for_route,
    start_agent_task,
)
from market_mapper.workflow.state import ResearchWorkflowState


def critic_verifier_node(state: ResearchWorkflowState) -> ResearchWorkflowState:
    """Execute the critic/verifier placeholder and update workflow state."""

    task = start_agent_task(
        state,
        agent_name="critic_verifier",
        task_type="verify_analysis",
        inputs={"comparison_result_id": state.comparison_result.id},
    )
    node_output = run_critic_verifier(
        CriticVerifierNodeInput(
            run_id=state.run.id,
            research_plan=state.session.research_plan,
            company_profiles=state.company_profiles,
            comparison_result=state.comparison_result,
        )
    )
    execute_sandbox_for_route(
        state,
        route_name="critic_verifier",
        target_agent_task=task,
        payload={
            "company_profiles": [
                profile.model_dump(mode="json")
                for profile in state.company_profiles
            ],
            "comparison_result": state.comparison_result.model_dump(mode="json"),
            "verification_result": node_output.verification_result.model_dump(mode="json"),
        },
    )
    state.verification_result = node_output.verification_result
    state.run.current_node = "critic_verifier"
    complete_agent_task(
        state,
        task=task,
        outputs={
            "verification_result_id": state.verification_result.id,
            "approved": state.verification_result.approved,
        },
        summary=node_output.summary,
    )
    return state
