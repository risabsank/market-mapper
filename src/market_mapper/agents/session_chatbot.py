"""OpenAI-powered Session Chatbot implementation."""

from __future__ import annotations

from pydantic import Field

from market_mapper.schemas.models.common import MarketMapperModel
from market_mapper.services import generate_structured_output, render_agent_input
from market_mapper.services.session_service import (
    ApprovedSessionSnapshot,
    SessionChatAnswer,
    SessionChatReference,
)
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
- For factual answers, cite supporting extracted claims, source documents, and report sections when available.
- Only cite ids or section headings that exist in the approved session state.
- Add an uncertainty_note when the evidence is partial, sparse, or directional.
"""


class SessionChatReadiness(MarketMapperModel):
    """Structured readiness confirmation for the sidebar chatbot."""

    chat_ready: bool
    summary: str


class SessionChatReferenceModel(MarketMapperModel):
    """Structured OpenAI evidence reference for one chat turn."""

    reference_type: str
    reference_id: str


class SessionChatAnswerModel(MarketMapperModel):
    """Structured OpenAI output for one chat turn."""

    answer: str
    references: list[SessionChatReferenceModel] = Field(default_factory=list)
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
    source_documents_by_id = {
        document.id: document for document in approved_state.source_documents
    }
    claims_by_id = {
        claim.id: claim
        for profile in approved_state.company_profiles
        for claim in profile.claims
    }
    report_sections_by_heading = {
        section.heading: section for section in approved_state.report.sections
    }
    references = _validate_references(
        references=response.references,
        source_documents_by_id=source_documents_by_id,
        claims_by_id=claims_by_id,
        report_sections_by_heading=report_sections_by_heading,
    )
    citation_ids = [
        citation_id
        for citation_id in response.citation_ids
        if citation_id in source_documents_by_id
    ]
    citation_ids.extend(
        reference.reference_id
        for reference in references
        if reference.reference_type == "source"
    )
    return SessionChatAnswer(
        answer=response.answer.strip(),
        references=references,
        citation_ids=_dedupe_preserving_order(citation_ids),
        uncertainty_note=response.uncertainty_note.strip() if response.uncertainty_note else None,
    )


def _validate_references(
    *,
    references: list[SessionChatReferenceModel],
    source_documents_by_id: dict[str, object],
    claims_by_id: dict[str, object],
    report_sections_by_heading: dict[str, object],
) -> list[SessionChatReference]:
    validated: list[SessionChatReference] = []
    for reference in references:
        reference_type = reference.reference_type.strip().lower()
        reference_id = reference.reference_id.strip()
        if not reference_id:
            continue
        if reference_type == "source":
            document = source_documents_by_id.get(reference_id)
            if document is None:
                continue
            validated.append(
                SessionChatReference(
                    reference_type="source",
                    reference_id=document.id,
                    label=document.title or document.id,
                    url=document.url,
                    snippet=document.snippet,
                )
            )
            continue
        if reference_type == "claim":
            claim = claims_by_id.get(reference_id)
            if claim is None:
                continue
            validated.append(
                SessionChatReference(
                    reference_type="claim",
                    reference_id=claim.id,
                    label=claim.label,
                    snippet=str(claim.value),
                )
            )
            continue
        if reference_type == "report_section":
            section = report_sections_by_heading.get(reference_id)
            if section is None:
                continue
            validated.append(
                SessionChatReference(
                    reference_type="report_section",
                    reference_id=section.heading,
                    label=section.heading,
                    snippet=section.body[:240] if section.body else None,
                )
            )
    return _dedupe_references(validated)


def _dedupe_references(references: list[SessionChatReference]) -> list[SessionChatReference]:
    seen: set[tuple[str, str]] = set()
    deduped: list[SessionChatReference] = []
    for reference in references:
        key = (reference.reference_type, reference.reference_id)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(reference)
    return deduped


def _dedupe_preserving_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped
