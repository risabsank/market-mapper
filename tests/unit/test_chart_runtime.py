from market_mapper.sandbox.contracts import SandboxExecutionRequest
from market_mapper.sandbox.runners.sandbox_runtime import LocalSandboxRuntime


def test_chart_runtime_renders_svg_artifacts(tmp_path) -> None:
    runtime = LocalSandboxRuntime()
    result = runtime.execute(
        SandboxExecutionRequest(
            route_name="chart_generation",
            run_id="run_test",
            sandbox_task_id="sandbox_chart",
            working_directory=str(tmp_path / "sandbox"),
            payload={
                "comparison_result": {
                    "id": "comparison_1",
                    "run_id": "run_test",
                    "company_ids": ["company_1"],
                    "dimensions": ["pricing", "features"],
                    "findings": [],
                    "similarities": [],
                    "differences": [],
                    "tradeoffs": [],
                    "ideal_customer_notes": [],
                },
                "chart_specs": [
                    {
                        "id": "chart_1",
                        "run_id": "run_test",
                        "chart_type": "bar",
                        "title": "Confidence",
                        "data": [{"company": "ExampleCo", "confidence": 0.8}],
                        "x_field": "company",
                        "y_field": "confidence",
                        "comparison_result_id": "comparison_1",
                    }
                ],
            },
        )
    )

    assert result.metadata["chart_count"] == 1
    assert any(artifact.content_type == "image/svg+xml" for artifact in result.artifacts)
