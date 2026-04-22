from market_mapper.sandbox.contracts import SandboxExecutionRequest
from market_mapper.sandbox.runners.sandbox_runtime import LocalSandboxRuntime
from market_mapper.research.fetchers import PageCapture


def test_web_research_runtime_emits_captured_source_documents(
    tmp_path,
    monkeypatch,
) -> None:
    def fake_capture_page_snapshot(*, target, output_dir, timeout_ms=30000):
        output_dir.mkdir(parents=True, exist_ok=True)
        html_path = output_dir / "example.html"
        screenshot_path = output_dir / "example.png"
        html_path.write_text(
            "<html><head><title>Example</title></head><body><h1>AI Support</h1><p>Pricing and automation details.</p></body></html>",
            encoding="utf-8",
        )
        screenshot_path.write_bytes(b"fake-image")
        return PageCapture(
            requested_url=target.url,
            final_url=target.url,
            title="Example",
            html_path=str(html_path),
            screenshot_path=str(screenshot_path),
            status_code=200,
        )

    monkeypatch.setattr(
        "market_mapper.sandbox.runners.sandbox_runtime.capture_page_snapshot",
        fake_capture_page_snapshot,
    )

    runtime = LocalSandboxRuntime()
    result = runtime.execute(
        SandboxExecutionRequest(
            route_name="web_research",
            run_id="run_123",
            sandbox_task_id="sandbox_123",
            working_directory=str(tmp_path / "sandbox"),
            payload={
                "research_plan": {
                    "market_query": "AI customer support",
                    "requested_company_count": 1,
                    "comparison_dimensions": ["pricing", "features"],
                },
                "company_candidates": [
                    {
                        "name": "ExampleCo",
                        "website": "https://example.com",
                        "rationale": "Relevant",
                        "score": 0.9,
                    }
                ],
                "source_documents": [],
                "existing_documents": [],
            },
        )
    )

    assert result.metadata["captured_count"] >= 1
    assert result.metadata["source_documents"][0]["url"].startswith("https://example.com")
    assert any(artifact.content_type == "text/html" for artifact in result.artifacts)
    assert any(artifact.content_type == "image/png" for artifact in result.artifacts)
