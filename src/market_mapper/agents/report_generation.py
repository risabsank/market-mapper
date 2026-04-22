"""OpenAI-powered Report Generation Agent implementation."""

from __future__ import annotations

from market_mapper.schemas.models import CompanyProfile, Report, ReportSection, SourceDocument
from market_mapper.services import generate_structured_output, render_agent_input
from market_mapper.workflow.contracts import (
    ReportGenerationNodeInput,
    ReportGenerationNodeOutput,
)

REPORT_SYSTEM_PROMPT = """
You are the Report Generation Agent for Market Mapper.

Create a structured report from the approved comparison state.

Rules:
- Write a clear title and executive summary.
- Create sections that are useful to founders and product teams.
- Include company summaries, structured comparison coverage, key takeaways, and source references.
- Keep the markdown_body aligned with the structured sections.
- Cite source document ids where possible.
"""


def run_report_generation(
    node_input: ReportGenerationNodeInput,
) -> ReportGenerationNodeOutput:
    """Create a validated Markdown report from the approved comparison state."""

    response = generate_structured_output(
        response_model=ReportGenerationNodeOutput,
        system_prompt=REPORT_SYSTEM_PROMPT,
        user_input=render_agent_input(
            task_description="Generate the structured report and markdown export.",
            context={
                "run_id": node_input.run_id,
                "research_plan": node_input.research_plan.model_dump(mode="json"),
                "company_profiles": [
                    profile.model_dump(mode="json")
                    for profile in node_input.company_profiles
                ],
                "comparison_result": node_input.comparison_result.model_dump(mode="json"),
                "source_documents": [
                    document.model_dump(mode="json")
                    for document in node_input.source_documents
                ],
            },
        ),
    )
    response.report = _validate_report(
        raw_report=response.report,
        run_id=node_input.run_id,
        company_profiles=node_input.company_profiles,
        source_documents=node_input.source_documents,
    )
    response.summary = (
        f"Report generation produced a Markdown report with {len(response.report.sections)} sections."
    )
    response.next_route = "executor"
    return response


def _validate_report(
    *,
    raw_report: Report,
    run_id: str,
    company_profiles: list[CompanyProfile],
    source_documents: list[SourceDocument],
) -> Report:
    valid_source_ids = {document.id for document in source_documents}
    canonical_sections = _canonical_sections(
        raw_report=raw_report,
        company_profiles=company_profiles,
        valid_source_ids=valid_source_ids,
    )
    source_document_ids = _collect_report_source_ids(canonical_sections, valid_source_ids)
    if not source_document_ids:
        source_document_ids = [document.id for document in source_documents]
    markdown_body = _render_markdown_report(
        title=raw_report.title or "Market Mapper Report",
        executive_summary=raw_report.executive_summary,
        sections=canonical_sections,
        source_documents=source_documents,
        source_document_ids=source_document_ids,
    )
    return Report(
        id=raw_report.id,
        run_id=run_id,
        title=raw_report.title or "Market Mapper Report",
        executive_summary=raw_report.executive_summary.strip(),
        sections=canonical_sections,
        markdown_body=markdown_body,
        source_document_ids=source_document_ids,
        created_at=raw_report.created_at,
    )


def _canonical_sections(
    *,
    raw_report: Report,
    company_profiles: list[CompanyProfile],
    valid_source_ids: set[str],
) -> list[ReportSection]:
    sections_by_heading: dict[str, ReportSection] = {}
    for section in raw_report.sections:
        heading = section.heading.strip() or "Untitled Section"
        body = section.body.strip()
        if not body:
            continue
        canonical = ReportSection(
            heading=heading,
            body=body,
            citation_ids=[
                citation_id
                for citation_id in section.citation_ids
                if citation_id in valid_source_ids
            ],
        )
        sections_by_heading[heading.lower()] = canonical

    if "company summaries" not in sections_by_heading:
        sections_by_heading["company summaries"] = ReportSection(
            heading="Company Summaries",
            body=_build_company_summaries(company_profiles),
            citation_ids=_dedupe_source_ids(
                source_id
                for profile in company_profiles
                for source_id in profile.source_document_ids
                if source_id in valid_source_ids
            ),
        )

    if "structured comparison" not in sections_by_heading:
        sections_by_heading["structured comparison"] = ReportSection(
            heading="Structured Comparison",
            body=_build_structured_comparison(company_profiles),
            citation_ids=_dedupe_source_ids(
                source_id
                for profile in company_profiles
                for source_id in profile.source_document_ids
                if source_id in valid_source_ids
            ),
        )

    if "key takeaways" not in sections_by_heading:
        sections_by_heading["key takeaways"] = ReportSection(
            heading="Key Takeaways",
            body=_build_key_takeaways(company_profiles),
            citation_ids=_dedupe_source_ids(
                source_id
                for profile in company_profiles
                for source_id in profile.source_document_ids
                if source_id in valid_source_ids
            ),
        )

    ordered_headings = [
        "executive summary",
        "company summaries",
        "structured comparison",
        "key takeaways",
    ]
    ordered_sections: list[ReportSection] = []
    added: set[str] = set()
    for heading in ordered_headings:
        section = sections_by_heading.get(heading)
        if section is not None:
            ordered_sections.append(section)
            added.add(heading)
    for heading, section in sections_by_heading.items():
        if heading not in added:
            ordered_sections.append(section)
    return ordered_sections


def _build_company_summaries(company_profiles: list[CompanyProfile]) -> str:
    lines: list[str] = []
    for profile in company_profiles:
        summary_bits = []
        if profile.product_summary:
            summary_bits.append(profile.product_summary)
        if profile.positioning_statement:
            summary_bits.append(f"Positioning: {profile.positioning_statement}")
        if profile.target_customers:
            summary_bits.append(f"Target customers: {', '.join(profile.target_customers)}")
        if profile.explicit_missing_fields:
            summary_bits.append(
                f"Missing public data: {', '.join(profile.explicit_missing_fields[:4])}"
            )
        summary = " ".join(summary_bits).strip() or "Public profile data is still sparse."
        lines.append(f"- **{profile.name}**: {summary}")
    return "\n".join(lines)


def _build_structured_comparison(company_profiles: list[CompanyProfile]) -> str:
    lines: list[str] = []
    for profile in company_profiles:
        features = ", ".join(profile.core_features[:4]) if profile.core_features else "not clearly disclosed"
        pricing = profile.pricing_model or "not clearly disclosed"
        differentiators = (
            ", ".join(profile.differentiators[:3]) if profile.differentiators else "not clearly disclosed"
        )
        lines.append(
            f"- **{profile.name}**: Pricing is {pricing}; core features include {features}; "
            f"key differentiators include {differentiators}."
        )
    return "\n".join(lines)


def _build_key_takeaways(company_profiles: list[CompanyProfile]) -> str:
    if not company_profiles:
        return "- Public data is too sparse to generate reliable takeaways."
    strongest = sorted(
        company_profiles,
        key=lambda profile: (profile.confidence, len(profile.strengths), len(profile.source_document_ids)),
        reverse=True,
    )
    lines = [
        f"- **{profile.name}** appears strongest where public evidence supports {', '.join(profile.strengths[:2]) or 'core product depth'}."
        for profile in strongest[:2]
    ]
    sparse = [profile.name for profile in company_profiles if profile.confidence < 0.3]
    if sparse:
        lines.append(
            f"- Evidence remains thin for {', '.join(sparse)}, so some comparisons should be treated as directional."
        )
    return "\n".join(lines)


def _collect_report_source_ids(
    sections: list[ReportSection],
    valid_source_ids: set[str],
) -> list[str]:
    return _dedupe_source_ids(
        citation_id
        for section in sections
        for citation_id in section.citation_ids
        if citation_id in valid_source_ids
    )


def _render_markdown_report(
    *,
    title: str,
    executive_summary: str,
    sections: list[ReportSection],
    source_documents: list[SourceDocument],
    source_document_ids: list[str],
) -> str:
    source_lookup = {document.id: document for document in source_documents}
    lines = [f"# {title}", "", "## Executive Summary", "", executive_summary.strip()]
    for section in sections:
        if section.heading.strip().lower() == "executive summary":
            continue
        lines.extend(["", f"## {section.heading}", "", section.body.strip()])
        if section.citation_ids:
            citation_line = ", ".join(f"`{citation_id}`" for citation_id in section.citation_ids)
            lines.extend(["", f"Sources: {citation_line}"])

    lines.extend(["", "## Source References", ""])
    for source_id in source_document_ids:
        document = source_lookup.get(source_id)
        if document is None:
            continue
        title_text = document.title or document.url
        lines.append(f"- `{source_id}` - [{title_text}]({document.url})")
    return "\n".join(lines).strip() + "\n"


def _dedupe_source_ids(source_ids) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for source_id in source_ids:
        if source_id in seen:
            continue
        seen.add(source_id)
        deduped.append(source_id)
    return deduped
