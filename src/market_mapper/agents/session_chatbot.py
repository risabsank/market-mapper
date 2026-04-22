"""OpenAI-powered Session Chatbot implementation."""

from __future__ import annotations

from pydantic import Field

from market_mapper.schemas.models.common import MarketMapperModel
from market_mapper.services import generate_structured_output, render_agent_input
from market_mapper.services.session_service import ApprovedSessionSnapshot, SessionChatAnswer
from market_mapper.workflow.contracts import SessionChatbotNodeInput, SessionChatbotNodeOutput

SESSION_CHATBOT_SYSTEM_PROMPT = """
You are the Session Chatbot initializer for Market Mapper.

Confirm that the session is ready for follow-up chat grounded in the current dashboard state.

Rules:
- Set chat_ready to true when the dashboard state is sufficient for follow-up questions.
- Keep the summary short and grounded in the provided dashboard state.
"""

SESSION_CHAT_ANSWER_SYSTEM_PROMPT = """
You are the Market Mapper session chatbot.

Answer follow-up questions using only the approved session state provided to you.

Rules:
- Use only the supplied approved session state.
- If the answer is not supported by the provided state, say so plainly.
- Keep answers concise and specific.
- Cite only source document ids that are directly relevant.
- Add an uncertainty_note when the evidence is partial, sparse, or directional.
"""


class SessionChatReadiness(MarketMapperModel):
    """Structured readiness confirmation for the sidebar chatbot."""

    chat_ready: bool
    summary: str


class SessionChatAnswerModel(MarketMapperModel):
    """Structured OpenAI output for one chat turn."""

    answer: str
    citation_ids: list[str] = Field(default_factory=list)
    uncertainty_note: str | None = None


def run_session_chatbot(node_input: SessionChatbotNodeInput) -> SessionChatbotNodeOutput:
    """Mark the session as chat-ready after dashboard generation."""

    response = generate_structured_output(
        response_model=SessionChatReadiness,
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
    return SessionChatbotNodeOutput(
        next_route="end",
        summary=response.summary,
        chat_ready=response.chat_ready,
    )


def answer_session_question(
    *,
    approved_state: ApprovedSessionSnapshot,
    question: str,
) -> SessionChatAnswer:
    """Answer one follow-up question from the approved session state only."""

    response = generate_structured_output(
        response_model=SessionChatAnswerModel,
        system_prompt=SESSION_CHAT_ANSWER_SYSTEM_PROMPT,
        user_input=render_agent_input(
            task_description="Answer this follow-up question from the current approved session state.",
            context={
                "question": question,
                "approved_session_state": approved_state.model_dump(mode="json"),
            },
        ),
    )
    valid_source_ids = {document.id for document in approved_state.source_documents}
    citation_ids = [
        citation_id
        for citation_id in response.citation_ids
        if citation_id in valid_source_ids
    ]
    return SessionChatAnswer(
        answer=response.answer.strip(),
        citation_ids=citation_ids,
        uncertainty_note=response.uncertainty_note.strip() if response.uncertainty_note else None,
    )
