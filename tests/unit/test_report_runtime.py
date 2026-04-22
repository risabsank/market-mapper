from market_mapper.sandbox.contracts import SandboxExecutionRequest
from market_mapper.sandbox.runners.sandbox_runtime import LocalSandboxRuntime


def test_report_runtime_emits_markdown_artifact_with_report_id(tmp_path) -> None:
    runtime = LocalSandboxRuntime()
    result = runtime.execute(
        SandboxExecutionRequest(
            route_name="report_generation",
            run_id="run_test",
            sandbox_task_id="sandbox_report",
            working_directory=str(tmp_path / "sandbox"),
            payload={
                "id": "report_1",
                "markdown_body": "# Report\n\nHello.",
            },
        )
    )

    assert result.metadata["report_id"] == "report_1"
    assert any(
        artifact.kind == "markdown_report" and artifact.metadata.get("report_id") == "report_1"
        for artifact in result.artifacts
    )
