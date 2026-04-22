from market_mapper.agents.chart_generation import run_chart_generation
from market_mapper.schemas.models import (
    CompanyProfile,
    ComparisonResult,
)
from market_mapper.workflow.contracts import ChartGenerationNodeInput, ChartGenerationNodeOutput


def test_chart_generation_validates_and_falls_back(monkeypatch) -> None:
    comparison_result = ComparisonResult(
        run_id="run_test",
        company_ids=["company_1"],
        dimensions=["pricing", "features"],
    )
    profile = CompanyProfile(
        id="company_1",
        name="ExampleCo",
        confidence=0.75,
        pricing_model="Contact sales",
        core_features=["AI agent"],
        source_document_ids=["source_1", "source_2"],
    )

    def fake_generate_structured_output(**kwargs):
        return ChartGenerationNodeOutput(
            next_route="executor",
            summary="raw chart output",
            chart_specs=[],
        )

    monkeypatch.setattr(
        "market_mapper.agents.chart_generation.generate_structured_output",
        fake_generate_structured_output,
    )

    output = run_chart_generation(
        ChartGenerationNodeInput(
            run_id="run_test",
            comparison_result=comparison_result,
            company_profiles=[profile],
        )
    )

    assert len(output.chart_specs) >= 1
    assert all(spec.run_id == "run_test" for spec in output.chart_specs)
    assert all(spec.comparison_result_id == comparison_result.id for spec in output.chart_specs)
    assert output.used_sandbox is True
