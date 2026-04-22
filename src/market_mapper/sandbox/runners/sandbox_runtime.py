"""Sandbox runtime for isolated execution tasks."""

from __future__ import annotations

from abc import ABC, abstractmethod
import json
from pathlib import Path

from market_mapper.schemas.models.common import ArtifactKind
from market_mapper.sandbox.artifacts.helpers import write_json_artifact, write_text_artifact
from market_mapper.sandbox.contracts import SandboxExecutionRequest, SandboxExecutionResult


class SandboxRuntime(ABC):
    """Abstract sandbox runtime."""

    @abstractmethod
    def execute(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        """Execute one sandbox request and return emitted artifacts."""


class LocalSandboxRuntime(SandboxRuntime):
    """Local runtime that isolates work by route into per-task working directories."""

    def execute(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        route_name = request.route_name
        working_dir = Path(request.working_directory)
        working_dir.mkdir(parents=True, exist_ok=True)
        if request.input_manifest_path:
            Path(request.input_manifest_path).write_text(
                json.dumps(request.payload, indent=2, sort_keys=True, default=str),
                encoding="utf-8",
            )

        handler = {
            "web_research": self._handle_web_research,
            "structured_extraction": self._handle_structured_extraction,
            "critic_verifier": self._handle_critic_verifier,
            "report_generation": self._handle_report_generation,
            "chart_generation": self._handle_chart_generation,
            "dashboard_builder": self._handle_dashboard_builder,
        }.get(route_name, self._handle_generic)

        result = handler(request)
        log_path = working_dir / "sandbox.log"
        if not log_path.exists():
            log_path.write_text(
                f"Completed sandbox route '{route_name}' for task {request.sandbox_task_id}.\n",
                encoding="utf-8",
            )
        result.log_path = str(log_path)
        output_manifest = working_dir / "output_manifest.json"
        output_manifest.write_text(
            json.dumps(
                {
                    "summary": result.summary,
                    "artifacts": [artifact.model_dump(mode="json") for artifact in result.artifacts],
                    "metadata": result.metadata,
                },
                indent=2,
                sort_keys=True,
                default=str,
            ),
            encoding="utf-8",
        )
        result.output_manifest_path = str(output_manifest)
        return result

    def _handle_web_research(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        working_dir = Path(request.working_directory)
        artifacts = [
            write_json_artifact(
                root_dir=working_dir,
                filename="web_research_manifest.json",
                label="Web research manifest",
                payload=request.payload,
                metadata={"route_name": request.route_name},
            ),
            write_text_artifact(
                root_dir=working_dir,
                filename="source_snapshot.txt",
                label="Source snapshot summary",
                content="Sandbox captured a placeholder browser research snapshot.",
                kind=ArtifactKind.PAGE_SNAPSHOT,
                metadata={"route_name": request.route_name},
            ),
        ]
        return SandboxExecutionResult(
            sandbox_task_id=request.sandbox_task_id,
            route_name=request.route_name,
            working_directory=str(working_dir),
            summary="Sandbox prepared browser-research artifacts.",
            artifacts=artifacts,
        )

    def _handle_structured_extraction(
        self, request: SandboxExecutionRequest
    ) -> SandboxExecutionResult:
        working_dir = Path(request.working_directory)
        artifacts = [
            write_json_artifact(
                root_dir=working_dir,
                filename="structured_extraction_input.json",
                label="Structured extraction input",
                payload=request.payload,
                metadata={"route_name": request.route_name},
            )
        ]
        return SandboxExecutionResult(
            sandbox_task_id=request.sandbox_task_id,
            route_name=request.route_name,
            working_directory=str(working_dir),
            summary="Sandbox preserved structured extraction inputs.",
            artifacts=artifacts,
        )

    def _handle_critic_verifier(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        working_dir = Path(request.working_directory)
        artifacts = [
            write_json_artifact(
                root_dir=working_dir,
                filename="verification_payload.json",
                label="Verification payload",
                payload=request.payload,
                metadata={"route_name": request.route_name},
            )
        ]
        return SandboxExecutionResult(
            sandbox_task_id=request.sandbox_task_id,
            route_name=request.route_name,
            working_directory=str(working_dir),
            summary="Sandbox stored verification payload for review.",
            artifacts=artifacts,
        )

    def _handle_report_generation(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        working_dir = Path(request.working_directory)
        markdown = request.payload.get("markdown_body", "# Report\n\nNo report content provided.")
        artifacts = [
            write_text_artifact(
                root_dir=working_dir,
                filename="report.md",
                label="Markdown report",
                content=markdown,
                kind=ArtifactKind.MARKDOWN_REPORT,
                content_type="text/markdown",
                metadata={"route_name": request.route_name},
            ),
            write_json_artifact(
                root_dir=working_dir,
                filename="report_payload.json",
                label="Report payload",
                payload=request.payload,
                metadata={"route_name": request.route_name},
            ),
        ]
        return SandboxExecutionResult(
            sandbox_task_id=request.sandbox_task_id,
            route_name=request.route_name,
            working_directory=str(working_dir),
            summary="Sandbox rendered report artifacts.",
            artifacts=artifacts,
        )

    def _handle_chart_generation(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        working_dir = Path(request.working_directory)
        artifacts = [
            write_json_artifact(
                root_dir=working_dir,
                filename="chart_specs.json",
                label="Chart specs",
                payload=request.payload,
                metadata={"route_name": request.route_name},
            ),
            write_text_artifact(
                root_dir=working_dir,
                filename="chart_render_summary.txt",
                label="Chart render summary",
                content="Sandbox prepared chart render inputs and outputs.",
                kind=ArtifactKind.CHART_IMAGE,
                metadata={"route_name": request.route_name},
            ),
        ]
        return SandboxExecutionResult(
            sandbox_task_id=request.sandbox_task_id,
            route_name=request.route_name,
            working_directory=str(working_dir),
            summary="Sandbox rendered chart artifacts.",
            artifacts=artifacts,
        )

    def _handle_dashboard_builder(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        working_dir = Path(request.working_directory)
        artifacts = [
            write_json_artifact(
                root_dir=working_dir,
                filename="dashboard_state.json",
                label="Dashboard preview payload",
                payload=request.payload,
                kind=ArtifactKind.DASHBOARD_PREVIEW,
                metadata={"route_name": request.route_name},
            )
        ]
        return SandboxExecutionResult(
            sandbox_task_id=request.sandbox_task_id,
            route_name=request.route_name,
            working_directory=str(working_dir),
            summary="Sandbox prepared dashboard preview artifacts.",
            artifacts=artifacts,
        )

    def _handle_generic(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        working_dir = Path(request.working_directory)
        artifacts = [
            write_json_artifact(
                root_dir=working_dir,
                filename="sandbox_payload.json",
                label="Sandbox payload",
                payload=request.payload,
                kind=ArtifactKind.OTHER,
                metadata={"route_name": request.route_name},
            )
        ]
        return SandboxExecutionResult(
            sandbox_task_id=request.sandbox_task_id,
            route_name=request.route_name,
            working_directory=str(working_dir),
            summary="Sandbox captured generic execution payload.",
            artifacts=artifacts,
        )
