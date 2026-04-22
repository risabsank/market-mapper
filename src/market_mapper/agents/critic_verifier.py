"""OpenAI-powered Critic and Verifier Agent implementation."""

from __future__ import annotations

from market_mapper.schemas.models import (
    ComparisonResult,
    CompanyProfile,
    VerificationIssue,
    VerificationResult,
)
from market_mapper.schemas.models.common import VerificationSeverity
from market_mapper.services import generate_structured_output, render_agent_input
from market_mapper.workflow.contracts import (
    CriticVerifierNodeInput,
    CriticVerifierNodeOutput,
)

CRITIC_SYSTEM_PROMPT = """
You are the Critic and Verifier Agent for Market Mapper.

Review whether the current analysis is complete enough to continue.

Rules:
- Set approved=true only when the research state is sufficient for report and chart generation.
- If there are meaningful gaps, set requires_retry=true and add specific next_actions.
- Route retry advice toward the most relevant stage: web_research, structured_extraction, or comparison.
- Flag unsupported claims, sparse evidence, and missing comparison coverage explicitly.
- Issues should be concrete and actionable.
"""


def run_critic_verifier(
    node_input: CriticVerifierNodeInput,
) -> CriticVerifierNodeOutput:
    """Review research quality and determine whether the workflow should retry."""

    response = generate_structured_output(
        response_model=CriticVerifierNodeOutput,
        system_prompt=CRITIC_SYSTEM_PROMPT,
        user_input=render_agent_input(
            task_description="Review whether the current research state is ready for output generation.",
            context={
                "run_id": node_input.run_id,
                "research_plan": node_input.research_plan.model_dump(mode="json"),
                "requested_dimensions": node_input.research_plan.comparison_dimensions,
                "company_profiles": [
                    profile.model_dump(mode="json")
                    for profile in node_input.company_profiles
                ],
                "comparison_result": node_input.comparison_result.model_dump(mode="json"),
            },
        ),
    )
    response.verification_result = _validate_verification_result(
        raw_result=response.verification_result,
        company_profiles=node_input.company_profiles,
        comparison_result=node_input.comparison_result,
        requested_dimensions=node_input.research_plan.comparison_dimensions,
        run_id=node_input.run_id,
    )
    response.summary = _build_summary(response.verification_result)
    response.next_route = "executor"
    return response


def _validate_verification_result(
    *,
    raw_result: VerificationResult,
    company_profiles: list[CompanyProfile],
    comparison_result: ComparisonResult,
    requested_dimensions: list[str],
    run_id: str,
) -> VerificationResult:
    valid_company_ids = {profile.id for profile in company_profiles}
    valid_claim_ids = {
        claim.id
        for profile in company_profiles
        for claim in profile.claims
    }
    deterministic_issues = _deterministic_issues(
        company_profiles=company_profiles,
        comparison_result=comparison_result,
        requested_dimensions=requested_dimensions,
        valid_company_ids=valid_company_ids,
        valid_claim_ids=valid_claim_ids,
    )
    merged_issues = _merge_issues(raw_result.issues, deterministic_issues)
    next_actions = _merge_actions(
        raw_result.next_actions,
        _actions_from_issues(merged_issues),
    )
    requires_retry = bool(
        raw_result.requires_retry
        or any(issue.severity in {VerificationSeverity.WARNING, VerificationSeverity.ERROR} for issue in merged_issues)
    )
    approved = bool(raw_result.approved and not requires_retry)
    return VerificationResult(
        id=raw_result.id,
        run_id=run_id,
        approved=approved,
        requires_retry=requires_retry,
        issues=merged_issues,
        next_actions=next_actions,
        reviewed_at=raw_result.reviewed_at,
    )


def _deterministic_issues(
    *,
    company_profiles: list[CompanyProfile],
    comparison_result: ComparisonResult,
    requested_dimensions: list[str],
    valid_company_ids: set[str],
    valid_claim_ids: set[str],
) -> list[VerificationIssue]:
    issues: list[VerificationIssue] = []
    findings_by_dimension = {finding.dimension: finding for finding in comparison_result.findings}

    for profile in company_profiles:
        if not profile.source_document_ids:
            issues.append(
                VerificationIssue(
                    severity=VerificationSeverity.ERROR,
                    message=f"{profile.name} has no traceable source documents.",
                    company_id=profile.id,
                    fix_target="web_research",
                )
            )
        if profile.confidence < 0.3:
            issues.append(
                VerificationIssue(
                    severity=VerificationSeverity.WARNING,
                    message=f"{profile.name} has low-confidence extraction and likely needs stronger evidence.",
                    company_id=profile.id,
                    fix_target="web_research",
                )
            )
        if len(profile.explicit_missing_fields) >= 5:
            issues.append(
                VerificationIssue(
                    severity=VerificationSeverity.WARNING,
                    message=(
                        f"{profile.name} is missing too many structured fields: "
                        + ", ".join(profile.explicit_missing_fields[:5])
                    ),
                    company_id=profile.id,
                    fix_target="structured_extraction",
                )
            )
        unsupported_claims = [
            claim.label
            for claim in profile.claims
            if not claim.source_document_ids
        ]
        if unsupported_claims:
            issues.append(
                VerificationIssue(
                    severity=VerificationSeverity.ERROR,
                    message=(
                        f"{profile.name} includes unsupported claims: "
                        + ", ".join(unsupported_claims[:3])
                    ),
                    company_id=profile.id,
                    fix_target="structured_extraction",
                )
            )

    canonical_dimensions = _canonical_dimensions(requested_dimensions)
    for dimension in canonical_dimensions:
        if dimension not in findings_by_dimension:
            issues.append(
                VerificationIssue(
                    severity=VerificationSeverity.WARNING,
                    message=f"Comparison is missing a finding for {dimension.replace('_', ' ')}.",
                    fix_target="comparison",
                )
            )

    for finding in comparison_result.findings:
        if finding.winner_company_id and finding.winner_company_id not in valid_company_ids:
            issues.append(
                VerificationIssue(
                    severity=VerificationSeverity.ERROR,
                    message=f"Comparison winner for {finding.dimension} does not match any known company.",
                    fix_target="comparison",
                )
            )
        invalid_claims = [
            claim_id for claim_id in finding.evidence_claim_ids
            if claim_id not in valid_claim_ids
        ]
        if invalid_claims:
            issues.append(
                VerificationIssue(
                    severity=VerificationSeverity.ERROR,
                    message=(
                        f"Comparison finding for {finding.dimension} cites unsupported claim IDs."
                    ),
                    fix_target="comparison",
                )
            )

    if not comparison_result.tradeoffs:
        issues.append(
            VerificationIssue(
                severity=VerificationSeverity.WARNING,
                message="Comparison is missing explicit tradeoffs.",
                fix_target="comparison",
            )
        )

    return issues


def _merge_issues(
    model_issues: list[VerificationIssue],
    deterministic_issues: list[VerificationIssue],
) -> list[VerificationIssue]:
    merged: list[VerificationIssue] = []
    seen: set[tuple[str, str | None, str | None]] = set()
    for issue in [*model_issues, *deterministic_issues]:
        key = (issue.message.strip().lower(), issue.company_id, issue.fix_target)
        if key in seen:
            continue
        seen.add(key)
        merged.append(issue)
    return merged


def _actions_from_issues(issues: list[VerificationIssue]) -> list[str]:
    priority_order = ["web_research", "structured_extraction", "comparison"]
    actions_by_target = {
        "web_research": "Retry web research to gather stronger public sources and source-backed evidence.",
        "structured_extraction": "Retry structured extraction to repair missing fields and unsupported claims.",
        "comparison": "Retry comparison to fill missing dimensions and unsupported findings.",
    }
    targets = {
        issue.fix_target
        for issue in issues
        if issue.fix_target in actions_by_target
        and issue.severity in {VerificationSeverity.WARNING, VerificationSeverity.ERROR}
    }
    return [actions_by_target[target] for target in priority_order if target in targets]


def _merge_actions(model_actions: list[str], deterministic_actions: list[str]) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for action in [*deterministic_actions, *model_actions]:
        normalized = " ".join(action.split()).strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        merged.append(normalized)
    return merged


def _canonical_dimensions(requested_dimensions: list[str]) -> list[str]:
    synonyms = {
        "target customers": "target_customers",
        "target_customers": "target_customers",
        "customer segments": "target_customers",
        "core features": "features",
        "feature set": "features",
        "weaknesses": "gaps",
        "weaknesses_or_gaps": "gaps",
    }
    resolved: list[str] = []
    for dimension in requested_dimensions:
        key = synonyms.get(dimension.strip().lower(), dimension.strip().lower().replace(" ", "_"))
        if key not in resolved:
            resolved.append(key)
    return resolved


def _build_summary(result: VerificationResult) -> str:
    if result.approved:
        return "Verification approved the research state for downstream outputs."
    if result.requires_retry and result.next_actions:
        return f"Verification requested retry: {result.next_actions[0]}"
    return "Verification found issues that require review before continuing."
