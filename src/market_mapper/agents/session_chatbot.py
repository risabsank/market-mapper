"""Session Chatbot placeholder implementation."""

from __future__ import annotations

from market_mapper.workflow.contracts import SessionChatbotNodeInput, SessionChatbotNodeOutput


def run_session_chatbot(node_input: SessionChatbotNodeInput) -> SessionChatbotNodeOutput:
    """Mark the session as chat-ready after dashboard generation."""

    return SessionChatbotNodeOutput(
        chat_ready=True,
        summary=(
            "Session chatbot placeholder is ready to answer from the approved dashboard "
            f"state {node_input.dashboard_state.id}."
        ),
        next_route="end",
    )
