"""OpenAI-powered Critic and Verifier Agent implementation."""

from __future__ import annotations

from market_mapper.services import generate_structured_output, render_agent_input
from market_mapper.workflow.contracts import (
    CriticVerifierNodeInput,
    CriticVerifierNodeOutput,
)

CRITIC_SYSTEM_PROMPT = """
You are the Critic and Verifier Agent for Market Mapper.

Review whether the current analysis is complete enough to continue.

Rules:
- Set approved=true only when the research state is sufficient for report and chart generation.
- If there are meaningful gaps, set requires_retry=true and add specific next_actions.
- Issues should be concrete and actionable.
"""


def run_critic_verifier(
    node_input: CriticVerifierNodeInput,
) -> CriticVerifierNodeOutput:
    """Review analysis quality with OpenAI."""

    response = generate_structured_output(
        response_model=CriticVerifierNodeOutput,
        system_prompt=CRITIC_SYSTEM_PROMPT,
        user_input=render_agent_input(
            task_description="Review whether the current research state is ready for output generation.",
            context={
                "run_id": node_input.run_id,
                "research_plan": node_input.research_plan.model_dump(mode="json"),
                "company_profiles": [
                    profile.model_dump(mode="json")
                    for profile in node_input.company_profiles
                ],
                "comparison_result": node_input.comparison_result.model_dump(mode="json"),
            },
        ),
    )
    response.verification_result.run_id = node_input.run_id
    response.next_route = "executor"
    return response

