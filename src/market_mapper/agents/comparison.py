"""OpenAI-powered Comparison Agent implementation."""

from __future__ import annotations

from collections import defaultdict

from market_mapper.schemas.models import CompanyProfile, ComparisonFinding
from market_mapper.services import generate_structured_output, render_agent_input
from market_mapper.workflow.contracts import ComparisonNodeInput, ComparisonNodeOutput

COMPARISON_SYSTEM_PROMPT = """
You are the Comparison Agent for Market Mapper.

Compare the normalized company profiles across the requested dimensions.

Rules:
- Produce structured findings for each dimension.
- Cover the requested comparison dimensions first, especially pricing, features, positioning,
  target customers, integrations, differentiators, strengths, and gaps when they are requested
  or clearly relevant.
- Summaries should be concise and decision-useful.
- Use evidence_claim_ids only for claims that actually support the finding.
- Do not select a winner when the evidence is too weak or too mixed.
- Do not claim certainty when data is weak.
"""


def run_comparison(node_input: ComparisonNodeInput) -> ComparisonNodeOutput:
    """Generate a validated comparison result from company profiles."""

    requested_dimensions = _resolve_dimensions(node_input)
    comparison_context = _build_comparison_context(node_input.company_profiles)
    valid_claim_ids = {
        claim.id
        for profile in node_input.company_profiles
        for claim in profile.claims
    }
    valid_company_ids = {profile.id for profile in node_input.company_profiles}

    response = generate_structured_output(
        response_model=ComparisonNodeOutput,
        system_prompt=COMPARISON_SYSTEM_PROMPT,
        user_input=render_agent_input(
            task_description="Compare the company profiles according to the research plan.",
            context={
                "run_id": node_input.run_id,
                "research_plan": node_input.research_plan.model_dump(mode="json"),
                "requested_dimensions": requested_dimensions,
                "comparison_context": comparison_context,
                "company_profiles": [
                    profile.model_dump(mode="json")
                    for profile in node_input.company_profiles
                ],
            },
        ),
    )
    response.comparison_result = _validate_comparison_result(
        node_output=response,
        company_profiles=node_input.company_profiles,
        requested_dimensions=requested_dimensions,
        valid_company_ids=valid_company_ids,
        valid_claim_ids=valid_claim_ids,
        run_id=node_input.run_id,
    )
    response.summary = (
        f"Comparison analyzed {len(response.comparison_result.company_ids)} companies across "
        f"{len(response.comparison_result.findings)} dimensions."
    )
    response.next_route = "executor"
    return response


def _resolve_dimensions(node_input: ComparisonNodeInput) -> list[str]:
    canonical_dimensions = [
        "pricing",
        "features",
        "positioning",
        "target_customers",
        "integrations",
        "differentiators",
        "strengths",
        "gaps",
    ]
    synonyms = {
        "target customers": "target_customers",
        "target_customers": "target_customers",
        "customer segments": "target_customers",
        "core features": "features",
        "feature set": "features",
        "weaknesses": "gaps",
        "weaknesses_or_gaps": "gaps",
        "gaps": "gaps",
    }
    resolved: list[str] = []
    for dimension in node_input.research_plan.comparison_dimensions:
        key = synonyms.get(dimension.strip().lower(), dimension.strip().lower().replace(" ", "_"))
        if key not in resolved:
            resolved.append(key)
    for dimension in canonical_dimensions:
        if dimension not in resolved:
            resolved.append(dimension)
    return resolved


def _build_comparison_context(company_profiles: list[CompanyProfile]) -> list[dict]:
    packets: list[dict] = []
    for profile in company_profiles:
        claims_by_label: dict[str, list[str]] = defaultdict(list)
        for claim in profile.claims:
            claims_by_label[claim.label].append(claim.id)
        packets.append(
            {
                "company_id": profile.id,
                "name": profile.name,
                "pricing_model": profile.pricing_model,
                "public_pricing_details": profile.public_pricing_details,
                "core_features": profile.core_features,
                "positioning_statement": profile.positioning_statement,
                "target_customers": profile.target_customers,
                "integrations": profile.integrations,
                "differentiators": profile.differentiators,
                "strengths": profile.strengths,
                "gaps": profile.weaknesses_or_gaps,
                "explicit_missing_fields": profile.explicit_missing_fields,
                "confidence": profile.confidence,
                "claim_ids_by_label": dict(claims_by_label),
            }
        )
    return packets


def _validate_comparison_result(
    *,
    node_output: ComparisonNodeOutput,
    company_profiles: list[CompanyProfile],
    requested_dimensions: list[str],
    valid_company_ids: set[str],
    valid_claim_ids: set[str],
    run_id: str,
):
    result = node_output.comparison_result
    result.run_id = run_id
    result.company_ids = [profile.id for profile in company_profiles]
    result.dimensions = requested_dimensions

    findings_by_dimension: dict[str, ComparisonFinding] = {}
    for finding in result.findings:
        canonical_dimension = finding.dimension.strip().lower().replace(" ", "_")
        if canonical_dimension not in requested_dimensions:
            continue
        finding.dimension = canonical_dimension
        if finding.winner_company_id not in valid_company_ids:
            finding.winner_company_id = None
        finding.evidence_claim_ids = [
            claim_id for claim_id in finding.evidence_claim_ids
            if claim_id in valid_claim_ids
        ]
        findings_by_dimension[canonical_dimension] = finding

    for dimension in requested_dimensions:
        if dimension in findings_by_dimension:
            continue
        findings_by_dimension[dimension] = _fallback_finding(
            dimension=dimension,
            company_profiles=company_profiles,
        )

    result.findings = [findings_by_dimension[dimension] for dimension in requested_dimensions]
    result.similarities = _dedupe_strings(result.similarities)
    result.differences = _dedupe_strings(result.differences)
    result.tradeoffs = _dedupe_strings(result.tradeoffs)
    result.ideal_customer_notes = _dedupe_strings(result.ideal_customer_notes)
    return result


def _fallback_finding(
    *,
    dimension: str,
    company_profiles: list[CompanyProfile],
) -> ComparisonFinding:
    covered_companies = []
    missing_companies = []
    for profile in company_profiles:
        if _profile_has_dimension_data(profile, dimension):
            covered_companies.append(profile.name)
        else:
            missing_companies.append(profile.name)
    if covered_companies and not missing_companies:
        summary = f"All compared companies have some public data for {dimension.replace('_', ' ')}."
    elif covered_companies:
        summary = (
            f"Public data for {dimension.replace('_', ' ')} is partial: "
            f"{', '.join(covered_companies)} have evidence, while {', '.join(missing_companies)} remain sparse."
        )
    else:
        summary = f"Public data for {dimension.replace('_', ' ')} is too sparse for a reliable comparison."
    return ComparisonFinding(
        dimension=dimension,
        summary=summary,
        winner_company_id=None,
        evidence_claim_ids=[],
        notes=[],
    )


def _profile_has_dimension_data(profile: CompanyProfile, dimension: str) -> bool:
    mapping = {
        "pricing": bool(profile.pricing_model or profile.public_pricing_details),
        "features": bool(profile.core_features),
        "positioning": bool(profile.positioning_statement),
        "target_customers": bool(profile.target_customers),
        "integrations": bool(profile.integrations),
        "differentiators": bool(profile.differentiators),
        "strengths": bool(profile.strengths),
        "gaps": bool(profile.weaknesses_or_gaps),
    }
    return mapping.get(dimension, True)


def _dedupe_strings(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        normalized = " ".join(value.split()).strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(normalized)
    return deduped
