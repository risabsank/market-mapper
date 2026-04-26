"""Sandbox runtime for isolated execution tasks."""

from __future__ import annotations

from abc import ABC, abstractmethod
import json
from pathlib import Path
from textwrap import dedent

from market_mapper.research import (
    build_research_targets,
    capture_page_snapshot,
    extract_page_content_from_file,
)
from market_mapper.charts.service import render_chart_artifacts, validate_chart_specs
from market_mapper.schemas.models import ChartSpec, ComparisonResult
from market_mapper.schemas.models import CompanyCandidate, CompanyProfile, ResearchPlan, SourceDocument
from market_mapper.schemas.models import DashboardState, VerificationResult
from market_mapper.schemas.models.common import ArtifactKind
from market_mapper.sandbox.artifacts.helpers import (
    register_file_artifact,
    write_json_artifact,
    write_text_artifact,
)
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
        research_plan = ResearchPlan.model_validate(request.payload.get("research_plan", {}))
        company_candidates = [
            CompanyCandidate.model_validate(candidate)
            for candidate in request.payload.get("company_candidates", [])
        ]
        suggested_documents = [
            SourceDocument.model_validate(document)
            for document in request.payload.get("source_documents", [])
        ]
        existing_documents = [
            SourceDocument.model_validate(document)
            for document in request.payload.get("existing_documents", [])
        ]
        targets = build_research_targets(
            research_plan=research_plan,
            company_candidates=company_candidates,
            suggested_documents=suggested_documents,
            existing_documents=existing_documents,
        )
        captures_dir = working_dir / "captures"
        captures_dir.mkdir(parents=True, exist_ok=True)
        artifacts = []
        source_documents = []
        failures = []
        for index, target in enumerate(targets, start=1):
            try:
                capture = capture_page_snapshot(target=target, output_dir=captures_dir)
                parsed = extract_page_content_from_file(
                    html_path=capture.html_path,
                    url=capture.final_url,
                    title=capture.title,
                )
            except Exception as exc:  # pragma: no cover - exercised in integration/runtime
                failures.append({"url": target.url, "error": str(exc), "company_name": target.company_name})
                continue

            html_label = f"{target.company_name} page HTML {index}"
            screenshot_label = f"{target.company_name} page snapshot {index}"
            text_filename = f"extracted_{index:02d}.txt"
            text_artifact = write_text_artifact(
                root_dir=working_dir,
                filename=text_filename,
                label=f"{target.company_name} extracted text {index}",
                content=parsed.extracted_text,
                kind=ArtifactKind.EXTRACTED_TEXT,
                metadata={
                    "company_name": target.company_name,
                    "requested_url": target.url,
                    "final_url": capture.final_url,
                },
            )
            html_artifact = register_file_artifact(
                path=capture.html_path,
                label=html_label,
                kind=ArtifactKind.PAGE_SNAPSHOT,
                content_type="text/html",
                metadata={
                    "company_name": target.company_name,
                    "requested_url": target.url,
                    "final_url": capture.final_url,
                    "source_type": target.source_type,
                },
            )
            artifacts.extend([html_artifact, text_artifact])
            screenshot_path = capture.screenshot_path
            if screenshot_path:
                artifacts.append(
                    register_file_artifact(
                        path=screenshot_path,
                        label=screenshot_label,
                        kind=ArtifactKind.PAGE_SNAPSHOT,
                        content_type="image/png",
                        metadata={
                            "company_name": target.company_name,
                            "requested_url": target.url,
                            "final_url": capture.final_url,
                            "source_type": target.source_type,
                        },
                    )
                )

            source_documents.append(
                {
                    "url": capture.final_url,
                    "title": parsed.title,
                    "source_type": target.source_type,
                    "snippet": parsed.snippet,
                    "metadata": {
                        "company_name": target.company_name,
                        "requested_url": target.url,
                        "source_rationale": target.rationale,
                        "status_code": capture.status_code,
                        "html_path": capture.html_path,
                        "screenshot_path": capture.screenshot_path,
                        "extracted_text_path": text_artifact.path,
                        "word_count": parsed.word_count,
                        "headings": parsed.headings,
                    },
                }
            )

        manifest_payload = {
            "target_count": len(targets),
            "captured_count": len(source_documents),
            "failures": failures,
            "source_documents": source_documents,
        }
        artifacts.append(
            write_json_artifact(
                root_dir=working_dir,
                filename="web_research_manifest.json",
                label="Web research manifest",
                payload=manifest_payload,
                metadata={"route_name": request.route_name},
            )
        )
        return SandboxExecutionResult(
            sandbox_task_id=request.sandbox_task_id,
            route_name=request.route_name,
            working_directory=str(working_dir),
            summary=(
                f"Sandbox captured {len(source_documents)} source pages"
                + (f" with {len(failures)} capture failures." if failures else ".")
            ),
            artifacts=artifacts,
            metadata=manifest_payload,
        )

    def _handle_structured_extraction(
        self, request: SandboxExecutionRequest
    ) -> SandboxExecutionResult:
        working_dir = Path(request.working_directory)
        company_candidates = [
            CompanyCandidate.model_validate(candidate)
            for candidate in request.payload.get("company_candidates", [])
        ]
        source_documents = [
            SourceDocument.model_validate(document)
            for document in request.payload.get("source_documents", [])
        ]
        company_profiles = [
            CompanyProfile.model_validate(profile)
            for profile in request.payload.get("company_profiles", [])
        ]
        profiles_by_name = {profile.name.strip().lower(): profile for profile in company_profiles}
        evidence_packets = []
        for candidate in company_candidates:
            company_key = candidate.name.strip().lower()
            profile = profiles_by_name.get(company_key)
            related_documents = [
                document
                for document in source_documents
                if str(document.metadata.get("company_name", "")).strip().lower() == company_key
            ]
            evidence_preview = []
            for document in related_documents[:5]:
                extracted_text_path = document.metadata.get("extracted_text_path")
                excerpt = None
                if extracted_text_path and Path(extracted_text_path).exists():
                    excerpt = Path(extracted_text_path).read_text(encoding="utf-8")[:1600]
                evidence_preview.append(
                    {
                        "source_document_id": document.id,
                        "title": document.title,
                        "url": document.url,
                        "snippet": document.snippet,
                        "excerpt": excerpt,
                    }
                )
            evidence_packets.append(
                {
                    "company_candidate_id": candidate.id,
                    "company_name": candidate.name,
                    "website": candidate.website,
                    "profile_id": profile.id if profile is not None else None,
                    "confidence": profile.confidence if profile is not None else None,
                    "missing_fields": profile.explicit_missing_fields if profile is not None else [],
                    "source_count": len(related_documents),
                    "evidence_preview": evidence_preview,
                }
            )
        artifacts = [
            write_json_artifact(
                root_dir=working_dir,
                filename="structured_extraction_input.json",
                label="Structured extraction input",
                payload=request.payload,
                metadata={"route_name": request.route_name},
            ),
            write_json_artifact(
                root_dir=working_dir,
                filename="structured_extraction_manifest.json",
                label="Structured extraction manifest",
                payload={
                    "company_count": len(company_candidates),
                    "profile_count": len(company_profiles),
                    "evidence_packets": evidence_packets,
                },
                metadata={"route_name": request.route_name},
            ),
        ]
        return SandboxExecutionResult(
            sandbox_task_id=request.sandbox_task_id,
            route_name=request.route_name,
            working_directory=str(working_dir),
            summary=(
                f"Sandbox assembled {len(evidence_packets)} structured extraction evidence packets "
                f"for downstream profile validation."
            ),
            artifacts=artifacts,
            metadata={
                "company_count": len(company_candidates),
                "profile_count": len(company_profiles),
                "evidence_packet_count": len(evidence_packets),
            },
        )

    def _handle_critic_verifier(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        working_dir = Path(request.working_directory)
        company_profiles = [
            CompanyProfile.model_validate(profile)
            for profile in request.payload.get("company_profiles", [])
        ]
        verification_result = VerificationResult.model_validate(request.payload.get("verification_result", {}))
        low_confidence = [
            {
                "name": profile.name,
                "confidence": profile.confidence,
                "missing_fields": profile.explicit_missing_fields,
            }
            for profile in company_profiles
            if profile.confidence < 0.7 or profile.explicit_missing_fields
        ]
        issue_summary = [
            {
                "severity": issue.severity,
                "message": issue.message,
                "fix_target": issue.fix_target,
            }
            for issue in verification_result.issues
        ]
        artifacts = [
            write_json_artifact(
                root_dir=working_dir,
                filename="verification_payload.json",
                label="Verification payload",
                payload=request.payload,
                metadata={"route_name": request.route_name},
            ),
            write_json_artifact(
                root_dir=working_dir,
                filename="verification_summary.json",
                label="Verification summary",
                payload={
                    "approved": verification_result.approved,
                    "requires_retry": verification_result.requires_retry,
                    "issue_summary": issue_summary,
                    "low_confidence_profiles": low_confidence,
                    "next_actions": verification_result.next_actions,
                },
                metadata={"route_name": request.route_name},
            ),
        ]
        return SandboxExecutionResult(
            sandbox_task_id=request.sandbox_task_id,
            route_name=request.route_name,
            working_directory=str(working_dir),
            summary=(
                f"Sandbox prepared a verification summary with {len(issue_summary)} issues and "
                f"{len(low_confidence)} low-confidence profiles."
            ),
            artifacts=artifacts,
            metadata={
                "approved": verification_result.approved,
                "requires_retry": verification_result.requires_retry,
                "issue_count": len(issue_summary),
            },
        )

    def _handle_report_generation(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        working_dir = Path(request.working_directory)
        markdown = request.payload.get("markdown_body", "# Report\n\nNo report content provided.")
        report_id = str(request.payload.get("id", ""))
        artifacts = [
            write_text_artifact(
                root_dir=working_dir,
                filename="report.md",
                label="Markdown report",
                content=markdown,
                kind=ArtifactKind.MARKDOWN_REPORT,
                content_type="text/markdown",
                metadata={
                    "route_name": request.route_name,
                    "report_id": report_id,
                },
            ),
            write_json_artifact(
                root_dir=working_dir,
                filename="report_payload.json",
                label="Report payload",
                payload=request.payload,
                metadata={
                    "route_name": request.route_name,
                    "report_id": report_id,
                },
            ),
        ]
        return SandboxExecutionResult(
            sandbox_task_id=request.sandbox_task_id,
            route_name=request.route_name,
            working_directory=str(working_dir),
            summary="Sandbox rendered report artifacts.",
            artifacts=artifacts,
            metadata={
                "report_id": report_id,
                "artifact_paths": [artifact.path for artifact in artifacts],
            },
        )

    def _handle_chart_generation(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        working_dir = Path(request.working_directory)
        comparison_result = ComparisonResult.model_validate(request.payload.get("comparison_result", {}))
        chart_specs = [
            ChartSpec.model_validate(chart_spec)
            for chart_spec in request.payload.get("chart_specs", [])
        ]
        chart_specs = validate_chart_specs(
            chart_specs=chart_specs,
            run_id=comparison_result.run_id,
            comparison_result=comparison_result,
        )
        artifacts, rendered_charts = render_chart_artifacts(
            root_dir=working_dir,
            chart_specs=chart_specs,
        )
        return SandboxExecutionResult(
            sandbox_task_id=request.sandbox_task_id,
            route_name=request.route_name,
            working_directory=str(working_dir),
            summary=f"Sandbox rendered {len(rendered_charts)} chart artifacts.",
            artifacts=artifacts,
            metadata={
                "rendered_charts": rendered_charts,
                "chart_count": len(rendered_charts),
            },
        )

    def _handle_dashboard_builder(self, request: SandboxExecutionRequest) -> SandboxExecutionResult:
        working_dir = Path(request.working_directory)
        dashboard_state = DashboardState.model_validate(request.payload)
        preview_markdown = dedent(
            f"""\
            # Dashboard Preview

            Session: `{dashboard_state.session_id}`
            Run: `{dashboard_state.run_id}`

            Executive Summary:
            {dashboard_state.executive_summary or "No executive summary provided."}

            ## Sections
            """
        ) + "\n".join(
            f"- **{section.title}** (`{section.key}`): {section.summary or 'No summary available.'}"
            for section in dashboard_state.sections
        )
        artifacts = [
            write_json_artifact(
                root_dir=working_dir,
                filename="dashboard_state.json",
                label="Dashboard preview payload",
                payload=request.payload,
                kind=ArtifactKind.DASHBOARD_PREVIEW,
                metadata={"route_name": request.route_name},
            ),
            write_text_artifact(
                root_dir=working_dir,
                filename="dashboard_preview.md",
                label="Dashboard preview summary",
                content=preview_markdown,
                kind=ArtifactKind.DASHBOARD_PREVIEW,
                content_type="text/markdown",
                metadata={
                    "route_name": request.route_name,
                    "dashboard_id": dashboard_state.id,
                },
            ),
        ]
        return SandboxExecutionResult(
            sandbox_task_id=request.sandbox_task_id,
            route_name=request.route_name,
            working_directory=str(working_dir),
            summary=(
                f"Sandbox prepared dashboard preview artifacts for {len(dashboard_state.sections)} sections."
            ),
            artifacts=artifacts,
            metadata={
                "dashboard_id": dashboard_state.id,
                "section_count": len(dashboard_state.sections),
            },
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
