"""Sandbox execution contracts, runtime adapters, and artifacts."""

from .contracts import SandboxExecutionRequest, SandboxExecutionResult, SandboxFileArtifact

__all__ = [
    "SandboxExecutionRequest",
    "SandboxExecutionResult",
    "SandboxFileArtifact",
    "SandboxService",
]


def __getattr__(name: str):
    """Resolve heavyweight sandbox exports lazily to avoid import cycles."""

    if name == "SandboxService":
        from .service import SandboxService

        return SandboxService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
