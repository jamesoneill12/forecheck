"""Validate that a rendered :class:`Example` preserves the facts of its latent scenario.

The direction of truth is latent -> labels -> text. These checks catch the failure
mode where a renderer (offline or LLM) drifts from the latent scenario it was given:
a financial amount that does not appear in the structured context, a destination that
was rendered with the wrong relationship, a context gap that leaked the fact it was
supposed to withhold, and so on.
"""

from __future__ import annotations

from forecheck.contracts import ContextGap, Example

__all__ = ["ValidationError", "assert_valid", "validate_example"]


class ValidationError(ValueError):
    """Raised by :func:`assert_valid` when an example fails validation."""


def _validate_tool_identity(example: Example) -> list[str]:
    if example.context.proposed_action.tool_name != example.latent.tool.name:
        return ["proposed_action.tool_name does not match latent.tool.name"]
    return []


def _validate_financial(example: Example) -> list[str]:
    latent, context = example.latent, example.context
    if latent.financial_amount > 0:
        if context.financial is None:
            return ["latent.financial_amount > 0 but context.financial is missing"]
        if abs(context.financial.amount - latent.financial_amount) > 1e-9:
            return ["context.financial.amount does not match latent.financial_amount"]
        return []
    if context.financial is not None and context.financial.amount > 0:
        return ["context.financial reports an amount but latent.financial_amount is 0"]
    return []


def _validate_destination(example: Example, gaps: frozenset[ContextGap]) -> list[str]:
    latent, context = example.latent, example.context
    if not latent.destination_present:
        if context.destination is not None:
            return ["latent.destination_present is False but context.destination is present"]
        return []
    if context.destination is None:
        return ["latent.destination_present is True but context.destination is missing"]
    issues: list[str] = []
    if context.destination.relationship is not latent.destination_relationship:
        issues.append("context.destination.relationship does not match latent")
    if (
        ContextGap.MISSING_DESTINATION_TRUST not in gaps
        and context.destination.trust is not latent.destination_trust
    ):
        issues.append("context.destination.trust does not match latent")
    return issues


def _validate_untrusted_content(example: Example) -> list[str]:
    if example.latent.untrusted_content_present != example.context.has_untrusted_content:
        return ["context untrusted-content presence does not match latent"]
    return []


def _validate_resources(example: Example, gaps: frozenset[ContextGap]) -> list[str]:
    latent, context = example.latent, example.context
    issues: list[str] = []
    if ContextGap.MISSING_RESOURCE_SENSITIVITY in gaps:
        if context.resources:
            issues.append("gap MISSING_RESOURCE_SENSITIVITY present but resources were rendered")
        return issues
    for resource in context.resources:
        if resource.sensitivity is not latent.resource_sensitivity:
            issues.append("resource sensitivity does not match latent.resource_sensitivity")
        if ContextGap.MISSING_REVERSIBILITY in gaps:
            if resource.reversible is not None:
                issues.append("gap MISSING_REVERSIBILITY present but reversible was set")
        elif resource.reversible is not None and resource.reversible != latent.resource_reversible:
            issues.append("resource.reversible does not match latent.resource_reversible")
    return issues


def _validate_gap_omissions(example: Example, gaps: frozenset[ContextGap]) -> list[str]:
    issues: list[str] = []
    context = example.context
    if ContextGap.MISSING_PRINCIPAL_ENTITLEMENTS in gaps and context.principal.entitlements:
        issues.append("gap MISSING_PRINCIPAL_ENTITLEMENTS present but entitlements were rendered")
    if ContextGap.MISSING_DELEGATED_SCOPES in gaps and context.agent.delegated_scopes:
        issues.append("gap MISSING_DELEGATED_SCOPES present but delegated_scopes were rendered")
    if ContextGap.MISSING_POLICY in gaps and context.policies:
        issues.append("gap MISSING_POLICY present but policies were rendered")
    if ContextGap.MISSING_OBJECTIVE in gaps and context.objective.text != "":
        issues.append("gap MISSING_OBJECTIVE present but objective.text was rendered")
    return issues


def _validate_trajectory(example: Example) -> list[str]:
    if len(example.context.trajectory) != example.latent.trajectory_length:
        return ["context.trajectory length does not match latent.trajectory_length"]
    return []


def validate_example(example: Example) -> list[str]:
    """Return every way ``example.context`` fails to preserve ``example.latent``.

    An empty list means the example is valid. This is intentionally a list of
    human-readable issues rather than an exception, so a caller can validate an entire
    shard and report every problem at once.
    """
    gaps = frozenset(example.latent.context_gaps)
    issues: list[str] = []
    issues += _validate_tool_identity(example)
    issues += _validate_financial(example)
    issues += _validate_destination(example, gaps)
    issues += _validate_untrusted_content(example)
    issues += _validate_resources(example, gaps)
    issues += _validate_gap_omissions(example, gaps)
    issues += _validate_trajectory(example)
    return issues


def assert_valid(example: Example) -> None:
    """Raise :class:`ValidationError` if ``example`` fails :func:`validate_example`."""
    issues = validate_example(example)
    if issues:
        raise ValidationError(f"example {example.example_id!r} failed validation: {issues}")
