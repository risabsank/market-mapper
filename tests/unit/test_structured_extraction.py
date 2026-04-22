from pathlib import Path

from market_mapper.agents.structured_extraction import run_structured_extraction
from market_mapper.schemas.models import (
    CompanyCandidate,
    CompanyProfile,
    ExtractedClaim,
    SourceDocument,
)
from market_mapper.workflow.contracts import (
    StructuredExtractionNodeInput,
    StructuredExtractionNodeOutput,
)


def test_structured_extraction_validates_claim_traceability(tmp_path: Path, monkeypatch) -> None:
    extracted_text_path = tmp_path / "example.txt"
    extracted_text_path.write_text("Pricing starts at contact sales.", encoding="utf-8")

    source_document = SourceDocument(
        id="source_1",
        url="https://example.com/pricing",
        title="Pricing",
        source_type="official_site",
        metadata={
            "company_name": "ExampleCo",
            "extracted_text_path": str(extracted_text_path),
        },
    )

    def fake_generate_structured_output(**kwargs):
        assert "Pricing starts at contact sales." in kwargs["user_input"]
        return StructuredExtractionNodeOutput(
            next_route="executor",
            summary="raw extraction output",
            company_profiles=[
                CompanyProfile(
                    name="ExampleCo",
                    pricing_model="Contact sales",
                    claims=[
                        ExtractedClaim(
                            label="Pricing",
                            value="Contact sales",
                            source_document_ids=["source_1"],
                            confidence=0.8,
                        ),
                        ExtractedClaim(
                            label="Bad claim",
                            value="Unsupported",
                            source_document_ids=["missing_source"],
                            confidence=0.9,
                        ),
                    ],
                    source_document_ids=["missing_source"],
                    confidence=0.9,
                )
            ],
        )

    monkeypatch.setattr(
        "market_mapper.agents.structured_extraction.generate_structured_output",
        fake_generate_structured_output,
    )

    output = run_structured_extraction(
        StructuredExtractionNodeInput(
            run_id="run_test",
            company_candidates=[
                CompanyCandidate(
                    name="ExampleCo",
                    website="example.com",
                    rationale="Relevant",
                    score=0.9,
                )
            ],
            source_documents=[source_document],
        )
    )

    profile = output.company_profiles[0]
    assert profile.website == "https://example.com/"
    assert profile.source_document_ids == ["source_1"]
    assert len(profile.claims) == 1
    assert profile.claims[0].source_document_ids == ["source_1"]
    assert "product_summary" in profile.explicit_missing_fields
    assert output.next_route == "executor"


def test_structured_extraction_adds_fallback_profile_for_missing_company(monkeypatch) -> None:
    def fake_generate_structured_output(**kwargs):
        return StructuredExtractionNodeOutput(
            next_route="executor",
            summary="raw extraction output",
            company_profiles=[],
        )

    monkeypatch.setattr(
        "market_mapper.agents.structured_extraction.generate_structured_output",
        fake_generate_structured_output,
    )

    output = run_structured_extraction(
        StructuredExtractionNodeInput(
            run_id="run_test",
            company_candidates=[
                CompanyCandidate(
                    name="FallbackCo",
                    website="fallbackco.com",
                    rationale="Relevant",
                    score=0.8,
                )
            ],
            source_documents=[],
        )
    )

    profile = output.company_profiles[0]
    assert profile.name == "FallbackCo"
    assert profile.website == "https://fallbackco.com/"
    assert "product_summary" in profile.explicit_missing_fields
    assert profile.confidence <= 0.15
