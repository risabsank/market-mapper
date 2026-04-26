from market_mapper.schemas.models import (
    ComparisonResult,
    CompanyProfile,
    Report,
    ResearchPlan,
    ResearchSession,
    SandboxArtifact,
    SandboxTask,
    WorkflowRun,
)
from market_mapper.schemas.models.common import ArtifactKind
from market_mapper.workflow.nodes.report_generation import report_generation_node
from market_mapper.workflow.state import ResearchWorkflowState


def test_report_generation_node_attaches_sandbox_artifact(monkeypatch) -> None:
    session = ResearchSession(
        user_id="demo-user",
        user_prompt="Analyze AI support tools.",
        research_plan=ResearchPlan(market_query="AI support tools"),
    )
    run = WorkflowRun(session_id=session.id)
    state = ResearchWorkflowState(
        session=session,
        run=run,
        company_profiles=[CompanyProfile(id="company_1", name="ExampleCo")],
        comparison_result=ComparisonResult(run_id=run.id),
        source_documents=[],
        sandbox_tasks=[
            SandboxTask(
                run_id=run.id,
                route_name="report_generation",
                purpose="Render and validate Markdown report artifacts.",
                output_manifest_path="/tmp/report_output_manifest.json",
            )
        ],
        sandbox_artifacts=[
            SandboxArtifact(
                run_id=run.id,
                kind=ArtifactKind.MARKDOWN_REPORT,
                label="Markdown report",
                path="/tmp/report.md",
                metadata={"report_id": "report_1"},
            )
        ],
    )

    monkeypatch.setattr(
        "market_mapper.workflow.nodes.report_generation.run_report_generation",
        lambda _: type(
            "Output",
            (),
            {
                "report": Report(
                    id="report_1",
                    run_id=run.id,
                    title="Report",
                    executive_summary="Summary",
                    sections=[],
                    markdown_body="# Report",
                ),
                "summary": "Generated report.",
            },
        )(),
    )
    monkeypatch.setattr(
        "market_mapper.workflow.nodes.report_generation.execute_sandbox_for_route",
        lambda **kwargs: [],
    )

    updated = report_generation_node(state)

    assert updated.report.artifact_id == updated.sandbox_artifacts[0].id
