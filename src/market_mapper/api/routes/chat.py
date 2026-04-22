"""Session chat routes bound to approved research state."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from market_mapper.agents.session_chatbot import answer_session_question
from market_mapper.services.session_service import SessionChatAnswer, SessionChatRequest, SessionStateService

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/answer", response_model=SessionChatAnswer)
def answer_chat_question(request: SessionChatRequest) -> SessionChatAnswer:
    """Answer a follow-up question from the current approved session state only."""

    service = SessionStateService()
    try:
        approved_state = service.resolve_chat_request(request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Approved session state not found: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return answer_session_question(
        approved_state=approved_state,
        question=request.question,
    )
