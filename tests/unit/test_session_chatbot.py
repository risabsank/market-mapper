from market_mapper.agents.session_chatbot import answer_session_question
from market_mapper.schemas.models import (
    ComparisonResult,
    DashboardState,
    Report,
    ResearchPlan,
    SourceDocument,
)
from market_mapper.services.session_service import ApprovedSessionSnapshot


def test_session_chatbot_filters_invalid_citations(monkeypatch) -> None:
    snapshot = ApprovedSessionSnapshot(
        session_id="session_1",
        run_id="run_1",
        user_prompt="Compare AI support tools.",
        research_plan=ResearchPlan(market_query="AI support"),
        dashboard_state=DashboardState(session_id="session_1", run_id="run_1"),
        executive_summary="Summary",
        comparison_result=ComparisonResult(run_id="run_1"),
        report=Report(
            run_id="run_1",
            title="Report",
            executive_summary="Summary",
            sections=[],
            markdown_body="# Report",
        ),
        source_documents=[
            SourceDocument(id="source_1", url="https://example.com", title="Example")
        ],
    )

    monkeypatch.setattr(
        "market_mapper.agents.session_chatbot.generate_structured_output",
        lambda **kwargs: type(
            "Response",
            (),
            {
                "answer": "Answer from approved state.",
                "citation_ids": ["source_1", "missing_source"],
                "uncertainty_note": "Directional where pricing is sparse.",
            },
        )(),
    )

    answer = answer_session_question(
        approved_state=snapshot,
        question="What is most uncertain?",
    )

    assert answer.answer == "Answer from approved state."
    assert answer.citation_ids == ["source_1"]
    assert answer.uncertainty_note == "Directional where pricing is sparse."
