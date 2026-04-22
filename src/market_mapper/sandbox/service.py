"""Trusted-harness service for sandbox-backed execution."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from market_mapper.config.settings import get_settings
from market_mapper.schemas.models import (
    SandboxArtifact,
    SandboxTask,
    SandboxValidationIssue,
    SandboxValidationResult,
)
from market_mapper.schemas.models.common import VerificationSeverity
from market_mapper.sandbox.artifacts import validate_file_artifacts
from market_mapper.sandbox.contracts import SandboxExecutionRequest
from market_mapper.sandbox.runners.sandbox_runtime import LocalSandboxRuntime, SandboxRuntime
from market_mapper.storage import FileWorkflowStateStore
from market_mapper.workflow.state import ResearchWorkflowState


class SandboxService:
    """Coordinate sandbox execution while keeping orchestration in the trusted harness."""

    def __init__(
        self,
        runtime: SandboxRuntime | None = None,
        root_dir: str | None = None,
        state_store: FileWorkflowStateStore | None = None,
    ) -> None:
        settings = get_settings()
        self.root_dir = Path(root_dir or settings.workflow_state_dir) / "sandbox_runs"
        self.runtime = runtime or LocalSandboxRuntime()
        self.state_store = state_store or FileWorkflowStateStore(settings.workflow_state_dir)

    def execute_route_tasks(
        self,
        *,
        state: ResearchWorkflowState,
        route_name: str,
        payload: dict[str, Any],
        target_agent_task_id: str,
    ) -> list[SandboxArtifact]:
        """Execute pending or resumable sandbox tasks for a route and persist artifacts in state."""

        artifacts: list[SandboxArtifact] = []
        for sandbox_task in self._pending_tasks_for_route(state, route_name):
            sandbox_task.agent_task_id = target_agent_task_id
            sandbox_task.working_directory = str(
                self._working_directory(state.run.id, sandbox_task.id)
            )
            input_payload = self._stringify_payload(payload)
            sandbox_task.set_input_payload(input_payload)
            sandbox_task.input_manifest_path = str(
                self._write_input_manifest(
                    sandbox_task=sandbox_task,
                    payload=input_payload,
                )
            )
            self._persist_sandbox_task(state, sandbox_task)
            sandbox_task.mark_running()
            self._persist_sandbox_task(state, sandbox_task)
            request = SandboxExecutionRequest(
                route_name=route_name,
                run_id=state.run.id,
                sandbox_task_id=sandbox_task.id,
                working_directory=sandbox_task.working_directory,
                input_manifest_path=sandbox_task.input_manifest_path,
                payload=payload,
            )
            try:
                result = self.runtime.execute(request)
            except Exception as exc:  # pragma: no cover - exercised once runtime is active
                sandbox_task.mark_failed(str(exc), resumable=True)
                self._persist_sandbox_task(state, sandbox_task)
                state.touch()
                continue

            sandbox_task.output_manifest_path = result.output_manifest_path
            validation_result = self._validate_result(result)
            sandbox_task.set_validation_result(validation_result)
            sandbox_task.output_paths = [artifact.path for artifact in result.artifacts]
            for file_artifact in result.artifacts:
                artifact = SandboxArtifact(
                    run_id=state.run.id,
                    kind=file_artifact.kind,
                    label=file_artifact.label,
                    path=file_artifact.path,
                    content_type=file_artifact.content_type,
                    source_task_id=target_agent_task_id,
                    metadata={k: str(v) for k, v in file_artifact.metadata.items()},
                )
                sandbox_task.add_artifact(artifact.id)
                state.run.add_artifact(artifact.id)
                artifacts.append(artifact)
                state.sandbox_artifacts.append(artifact)
                self.state_store.save_artifact(artifact)

            if validation_result.valid:
                sandbox_task.mark_completed()
            else:
                sandbox_task.mark_failed(
                    "Sandbox output validation failed.",
                    resumable=False,
                )
            self._persist_sandbox_task(state, sandbox_task)
            state.touch()
        return artifacts

    def _validate_result(self, result) -> SandboxValidationResult:
        issues = [
            SandboxValidationIssue(
                severity=VerificationSeverity.ERROR,
                message=issue,
            )
            for issue in validate_file_artifacts(result.artifacts)
        ]
        return SandboxValidationResult(valid=not issues, issues=issues)

    def _write_input_manifest(self, *, sandbox_task: SandboxTask, payload: dict[str, str]) -> Path:
        working_dir = Path(sandbox_task.working_directory or self.root_dir / sandbox_task.id)
        working_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = working_dir / "input_manifest.json"
        manifest_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, default=str),
            encoding="utf-8",
        )
        return manifest_path

    def _pending_tasks_for_route(
        self, state: ResearchWorkflowState, route_name: str
    ) -> list[SandboxTask]:
        return [
            sandbox_task
            for sandbox_task in state.sandbox_tasks
            if sandbox_task.route_name == route_name
            and sandbox_task.status.value in {"pending", "resumable"}
        ]

    def _working_directory(self, run_id: str, sandbox_task_id: str) -> Path:
        return self.root_dir / run_id / sandbox_task_id

    def _stringify_payload(self, payload: dict[str, Any]) -> dict[str, str]:
        return {key: json.dumps(value, default=str) for key, value in payload.items()}

    def _persist_sandbox_task(self, state: ResearchWorkflowState, sandbox_task: SandboxTask) -> None:
        self.state_store.update_sandbox_task(sandbox_task)
        self.state_store.save_run(state.run)
