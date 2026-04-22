"""Helpers for writing sandbox artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from market_mapper.schemas.models.common import ArtifactKind
from market_mapper.sandbox.contracts import SandboxFileArtifact


def write_json_artifact(
    *,
    root_dir: Path,
    filename: str,
    label: str,
    payload: Any,
    kind: ArtifactKind = ArtifactKind.STRUCTURED_JSON,
    metadata: dict[str, Any] | None = None,
) -> SandboxFileArtifact:
    """Write a JSON artifact into the sandbox working directory."""

    root_dir.mkdir(parents=True, exist_ok=True)
    path = root_dir / filename
    path.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str), encoding="utf-8")
    return SandboxFileArtifact(
        kind=kind,
        label=label,
        path=str(path),
        content_type="application/json",
        metadata=metadata or {},
    )


def write_text_artifact(
    *,
    root_dir: Path,
    filename: str,
    label: str,
    content: str,
    kind: ArtifactKind,
    content_type: str = "text/plain",
    metadata: dict[str, Any] | None = None,
) -> SandboxFileArtifact:
    """Write a text artifact into the sandbox working directory."""

    root_dir.mkdir(parents=True, exist_ok=True)
    path = root_dir / filename
    path.write_text(content, encoding="utf-8")
    return SandboxFileArtifact(
        kind=kind,
        label=label,
        path=str(path),
        content_type=content_type,
        metadata=metadata or {},
    )


def register_file_artifact(
    *,
    path: str | Path,
    label: str,
    kind: ArtifactKind,
    content_type: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> SandboxFileArtifact:
    """Register an already-written file as a sandbox artifact."""

    resolved_path = Path(path)
    return SandboxFileArtifact(
        kind=kind,
        label=label,
        path=str(resolved_path),
        content_type=content_type,
        metadata=metadata or {},
    )


def validate_file_artifacts(artifacts: list[SandboxFileArtifact]) -> list[str]:
    """Validate that declared artifact paths exist on disk."""

    issues: list[str] = []
    for artifact in artifacts:
        if not Path(artifact.path).exists():
            issues.append(f"Artifact path does not exist: {artifact.path}")
    return issues
