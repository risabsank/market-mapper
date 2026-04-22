"""Critic and Verifier Agent placeholder implementation."""

from __future__ import annotations

from market_mapper.schemas.models import VerificationIssue, VerificationResult
from market_mapper.schemas.models.common import VerificationSeverity
from market_mapper.workflow.contracts import (
    CriticVerifierNodeInput,
    CriticVerifierNodeOutput,
)


def run_critic_verifier(
    node_input: CriticVerifierNodeInput,
) -> CriticVerifierNodeOutput:
    """Approve placeholder analysis when basic prerequisites exist."""

    issues = []
    approved = True
    requires_retry = False

    if not node_input.company_profiles:
        approved = False
        requires_retry = True
        issues.append(
            VerificationIssue(
                severity=VerificationSeverity.ERROR,
                message="No company profiles available for verification.",
                fix_target="structured_extraction",
            )
        )

    verification_result = VerificationResult(
        run_id=node_input.run_id,
        approved=approved,
        requires_retry=requires_retry,
        issues=issues,
        next_actions=[] if approved else ["Retry structured extraction."],
    )

    return CriticVerifierNodeOutput(
        verification_result=verification_result,
        summary="Critic/verifier placeholder completed review.",
        next_route="executor",
    )
