"""OpenAI-powered Session Chatbot implementation."""

from __future__ import annotations

from market_mapper.services import generate_structured_output, render_agent_input
from market_mapper.workflow.contracts import SessionChatbotNodeInput, SessionChatbotNodeOutput

SESSION_CHATBOT_SYSTEM_PROMPT = """
You are the Session Chatbot initializer for Market Mapper.

Confirm that the session is ready for follow-up chat grounded in the current dashboard state.

Rules:
- Set chat_ready to true when the dashboard state is sufficient for follow-up questions.
- Keep the summary short and grounded in the provided dashboard state.
"""


def run_session_chatbot(node_input: SessionChatbotNodeInput) -> SessionChatbotNodeOutput:
    """Mark the session as chat-ready after dashboard generation."""

    response = generate_structured_output(
        response_model=SessionChatbotNodeOutput,
        system_prompt=SESSION_CHATBOT_SYSTEM_PROMPT,
        user_input=render_agent_input(
            task_description="Confirm session chatbot readiness.",
            context={
                "session_id": node_input.session_id,
                "run_id": node_input.run_id,
                "dashboard_state": node_input.dashboard_state.model_dump(mode="json"),
            },
        ),
    )
    response.next_route = "end"
    return response

