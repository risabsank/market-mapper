"""Session chat routes bound to approved research state."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from market_mapper.agents.session_chatbot import answer_session_question
from market_mapper.auth import AuthenticatedUser, CurrentUser
from market_mapper.services import AuthorizationError
from market_mapper.services.session_service import (
    DemoSessionChatRequest,
    SessionChatAnswer,
    SessionChatRequest,
    SessionStateService,
)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/answer", response_model=SessionChatAnswer)
def answer_chat_question(
    request: SessionChatRequest,
    user: AuthenticatedUser = CurrentUser,
) -> SessionChatAnswer:
    """Answer a follow-up question from the current approved session state only."""

    service = SessionStateService()
    try:
        approved_state = service.resolve_chat_request(request)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Approved session state not found: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if approved_state.user_id != user.user_id:
        raise HTTPException(status_code=403, detail="This session is not available to this user.")

    return answer_session_question(
        approved_state=approved_state,
        question=request.question,
    )


@router.post("/demo-answer", response_model=SessionChatAnswer)
def answer_demo_chat_question(request: DemoSessionChatRequest) -> SessionChatAnswer:
    """Answer a follow-up question from inline approved state for local demo use only."""

    service = SessionStateService()
    approved_state = service.resolve_demo_chat_request(request)
    return answer_session_question(
        approved_state=approved_state,
        question=request.question,
    )
