from market_mapper.agents.session_chatbot import answer_session_question
from market_mapper.schemas.models import (
    CompanyProfile,
    ComparisonResult,
    DashboardState,
    ExtractedClaim,
    Report,
    ReportSection,
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
        company_profiles=[
            CompanyProfile(
                id="company_1",
                name="ExampleCo",
                claims=[
                    ExtractedClaim(
                        id="claim_1",
                        label="Pricing transparency",
                        value="ExampleCo exposes public starter pricing.",
                        source_document_ids=["source_1"],
                    )
                ],
                source_document_ids=["source_1"],
            )
        ],
        comparison_result=ComparisonResult(run_id="run_1"),
        report=Report(
            run_id="run_1",
            title="Report",
            executive_summary="Summary",
            sections=[
                ReportSection(
                    heading="Key Takeaways",
                    body="ExampleCo is strongest where pricing transparency matters.",
                    citation_ids=["source_1"],
                )
            ],
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
                "references": [
                    type("Reference", (), {"reference_type": "claim", "reference_id": "claim_1"})(),
                    type("Reference", (), {"reference_type": "source", "reference_id": "source_1"})(),
                    type("Reference", (), {"reference_type": "report_section", "reference_id": "Key Takeaways"})(),
                    type("Reference", (), {"reference_type": "source", "reference_id": "missing_source"})(),
                ],
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
    assert [(reference.reference_type, reference.reference_id) for reference in answer.references] == [
        ("claim", "claim_1"),
        ("source", "source_1"),
        ("report_section", "Key Takeaways"),
    ]
    assert answer.uncertainty_note == "Directional where pricing is sparse."
