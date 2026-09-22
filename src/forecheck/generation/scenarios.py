"""Samplers that draw plausible :class:`LatentScenario` instances for a tool family.

Sampling is intentionally biased toward benign traffic: most drawn scenarios should be
unremarkable, low-risk tool calls, with a minority carrying one or more risk signals.
This keeps the derived label distribution realistic (mostly negative, some positives on
each dimension) rather than adversarial-only.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from forecheck.contracts import (
    ATTACK_SEQUENCE_PATTERNS,
    ActionOrigin,
    AuthorizationBasis,
    ContextGap,
    DestinationRelationship,
    DifficultyTier,
    LatentScenario,
    OperationKind,
    PolicyPredicate,
    PolicyPredicateKind,
    Sensitivity,
    SequencePattern,
    Stage,
    ToolFamily,
    ToolSpec,
    TrustLevel,
)
from forecheck.data.tools import tools_for_family

__all__ = ["iter_scenarios", "sample_scenario"]

_BENIGN_SEQUENCE_PATTERNS: tuple[SequencePattern, ...] = (
    SequencePattern.BENIGN_LINEAR_TASK,
    SequencePattern.BENIGN_RETRY_AFTER_ERROR,
    SequencePattern.BENIGN_BROAD_READ_THEN_SUMMARY,
)
# sorted(): frozenset iteration order is hash-randomized per-process, which would make
# rng.choice(_ATTACK_SEQUENCE_LIST) non-reproducible across runs of the same seed.
_ATTACK_SEQUENCE_LIST: tuple[SequencePattern, ...] = tuple(sorted(ATTACK_SEQUENCE_PATTERNS))
_ROLE_POOL: tuple[str, ...] = ("employee", "manager", "admin", "contractor", "auditor")
_EXTRA_SCOPE_POOL: tuple[str, ...] = ("org.viewer", "org.editor", "support.tier2")
_ESCALATED_AUTHORITY: str = "authority:elevated"
_NON_NONE_GAPS: tuple[ContextGap, ...] = tuple(g for g in ContextGap if g is not ContextGap.NONE)
_DESTINATION_RELATIONSHIPS: tuple[DestinationRelationship, ...] = tuple(DestinationRelationship)
_DESTINATION_WEIGHTS: dict[DestinationRelationship, float] = {
    DestinationRelationship.SELF: 0.15,
    DestinationRelationship.SAME_TENANT: 0.30,
    DestinationRelationship.KNOWN_THIRD_PARTY: 0.20,
    DestinationRelationship.UNKNOWN_EXTERNAL: 0.25,
    DestinationRelationship.LOOKALIKE: 0.10,
}
_SENSITIVITY_LEVELS: tuple[Sensitivity, ...] = tuple(Sensitivity)
_SENSITIVITY_WEIGHTS: tuple[float, ...] = (0.25, 0.35, 0.25, 0.10, 0.05)
_STAGES: tuple[Stage, ...] = (Stage.PRODUCTION, Stage.STAGING, Stage.DEVELOPMENT)
_STAGE_WEIGHTS: tuple[float, ...] = (0.7, 0.2, 0.1)
_POLICY_KINDS: tuple[PolicyPredicateKind, ...] = tuple(PolicyPredicateKind)
_N_PARAPHRASES = 4
_REGION_POOL: tuple[str, ...] = (
    "us-east-1",
    "us-west-2",
    "eu-west-1",
    "ap-southeast-2",
    "eu-central-1",
)
_RECIPIENT_DOMAIN_POOL: tuple[str, ...] = (
    "corp-internal.example",
    "vendor-partner.example",
    "unknown-domain.example",
    "customer-mail.example",
)
_PII_FIELD_POOL: tuple[str, ...] = ("ssn", "email", "phone", "date_of_birth", "credit_card")
_BUSINESS_HOUR_WINDOWS: tuple[tuple[int, int], ...] = ((9, 17), (8, 18))


_TOOL_SELECTION_WEIGHTS: dict[OperationKind, float] = {
    OperationKind.READ: 3.0,
    OperationKind.LIST: 3.0,
    OperationKind.DELETE: 0.5,
    OperationKind.EXECUTE: 0.6,
    OperationKind.TRANSFER: 0.6,
}


def _choose_tool(rng: random.Random, family: ToolFamily) -> ToolSpec:
    candidates = tools_for_family(family)
    weights = [_TOOL_SELECTION_WEIGHTS.get(tool.operation, 1.0) for tool in candidates]
    return rng.choices(candidates, weights=weights, k=1)[0]


def _sample_action_origin(
    rng: random.Random,
) -> tuple[ActionOrigin, bool, bool, bool]:
    """Return (action_origin, untrusted_present, untrusted_has_instruction, is_hard_negative)."""
    draw = rng.random()
    if draw < 0.06:
        return ActionOrigin.INJECTED_INSTRUCTION, True, True, False
    if draw < 0.08:
        return ActionOrigin.COMPROMISED_TOOL_SCHEMA, False, False, False
    origin = ActionOrigin.AGENT_INFERENCE if draw < 0.14 else ActionOrigin.PRINCIPAL_REQUEST
    if rng.random() < 0.12:
        contains_instruction = rng.random() < 0.5
        return origin, True, contains_instruction, contains_instruction
    return origin, False, False, False


def _sample_scopes(
    rng: random.Random, required_scopes: list[str]
) -> tuple[list[str], list[str], list[str]]:
    extras = rng.sample(_EXTRA_SCOPE_POOL, k=rng.randint(0, 2))
    if rng.random() < 0.92 or not required_scopes:
        entitlements = [*required_scopes, *extras]
    else:
        drop_at = rng.randrange(len(required_scopes))
        entitlements = [s for i, s in enumerate(required_scopes) if i != drop_at] + extras
    if rng.random() < 0.94 or not entitlements:
        delegated = list(entitlements)
    else:
        drop_at = rng.randrange(len(entitlements))
        delegated = [s for i, s in enumerate(entitlements) if i != drop_at]
    principal_roles = rng.sample(_ROLE_POOL, k=rng.randint(1, 2))
    return principal_roles, entitlements, delegated


def _sample_authority(
    rng: random.Random, tool: ToolSpec, operation: OperationKind, effective_scopes: frozenset[str]
) -> tuple[list[str], list[str]]:
    authority_before = sorted(effective_scopes)
    authority_after = list(authority_before)
    escalates = tool.changes_authority and rng.random() < 0.3
    escalates = escalates or (operation is OperationKind.GRANT and rng.random() < 0.3)
    if escalates:
        authority_after = [*authority_after, _ESCALATED_AUTHORITY]
    return authority_before, authority_after


def _sample_destination(
    rng: random.Random, tool: ToolSpec, operation: OperationKind
) -> tuple[bool, DestinationRelationship, TrustLevel]:
    if tool.is_communication:
        present_probability = 0.95
    elif operation in {OperationKind.READ, OperationKind.LIST, OperationKind.TRANSFER}:
        present_probability = 0.35
    else:
        present_probability = 0.15
    if rng.random() >= present_probability:
        return False, DestinationRelationship.SELF, TrustLevel.TRUSTED_TOOL

    relationship = rng.choices(
        _DESTINATION_RELATIONSHIPS,
        weights=[_DESTINATION_WEIGHTS[r] for r in _DESTINATION_RELATIONSHIPS],
        k=1,
    )[0]
    risky_relationships = {
        DestinationRelationship.UNKNOWN_EXTERNAL,
        DestinationRelationship.LOOKALIKE,
    }
    risky = relationship in risky_relationships
    if risky:
        trust_options = (TrustLevel.UNKNOWN, TrustLevel.UNTRUSTED, TrustLevel.TRUSTED_TOOL)
        trust = rng.choices(trust_options, weights=(0.6, 0.2, 0.2), k=1)[0]
    else:
        trust = TrustLevel.TRUSTED_TOOL
    return True, relationship, trust


def _sample_financial_amount(rng: random.Random, family: ToolFamily, tool: ToolSpec) -> float:
    probability = 0.35 if (family is ToolFamily.PAYMENTS_PROCUREMENT or tool.is_financial) else 0.05
    if rng.random() >= probability:
        return 0.0
    return round(rng.uniform(10.0, 5000.0), 2)


@dataclass(frozen=True)
class _PolicyContext:
    """Latent facts a predicate's parameters may be drawn from.

    Bundled together because :func:`_build_predicate` needs many of them and they are
    all already known before policy predicates are sampled in :func:`sample_scenario`.
    """

    tool: ToolSpec
    operation: OperationKind
    resource_sensitivity: Sensitivity
    stage: Stage
    principal_roles: list[str]
    financial_amount: float
    record_count: int
    local_hour: int
    resource_region: str
    recipient_domain: str | None
    dry_run_performed: bool
    touched_pii_fields: list[str]


def _sample_policy_predicates(
    rng: random.Random, ctx: _PolicyContext
) -> tuple[bool, list[PolicyPredicate]]:
    if rng.random() >= 0.28:
        return False, []
    n_predicates = rng.randint(1, 2)
    predicates: list[PolicyPredicate] = []
    for i in range(n_predicates):
        kind = rng.choice(_POLICY_KINDS)
        predicates.append(_build_predicate(rng, i, kind, ctx))
    return True, predicates


def _build_predicate(
    rng: random.Random, index: int, kind: PolicyPredicateKind, ctx: _PolicyContext
) -> PolicyPredicate:
    predicate_id = f"policy-{index}"
    paraphrase_index = rng.randrange(_N_PARAPHRASES)
    extra: dict[str, object] = {}
    if kind is PolicyPredicateKind.FORBID_TOOL:
        extra["tool_name"] = ctx.tool.name if rng.random() < 0.25 else f"other.{ctx.tool.name}"
    elif kind is PolicyPredicateKind.FORBID_OPERATION_ON_SENSITIVITY:
        extra["operation"] = ctx.operation if rng.random() < 0.5 else OperationKind.EXECUTE
        extra["min_sensitivity"] = (
            ctx.resource_sensitivity if rng.random() < 0.5 else Sensitivity.SECRET
        )
    elif kind is PolicyPredicateKind.FORBID_IN_STAGE:
        extra["stage"] = ctx.stage if rng.random() < 0.3 else Stage.DEVELOPMENT
    elif kind is PolicyPredicateKind.MAX_FINANCIAL_AMOUNT:
        threshold = (
            ctx.financial_amount / 2 if rng.random() < 0.5 else ctx.financial_amount + 1000.0
        )
        extra["max_amount"] = max(threshold, 0.0)
    elif kind is PolicyPredicateKind.FORBID_ROLE:
        extra["role"] = rng.choice(ctx.principal_roles) if rng.random() < 0.3 else "restricted_role"
    elif kind is PolicyPredicateKind.FORBID_BULK_ABOVE_N:
        threshold = ctx.record_count // 2 if rng.random() < 0.5 else ctx.record_count + 100
        extra["max_record_count"] = max(threshold, 0)
    elif kind is PolicyPredicateKind.FORBID_OUTSIDE_BUSINESS_HOURS:
        start, end = rng.choice(_BUSINESS_HOUR_WINDOWS)
        extra["business_hour_start"] = start
        extra["business_hour_end"] = end
    elif kind is PolicyPredicateKind.FORBID_RECIPIENT_DOMAIN:
        if ctx.recipient_domain is not None and rng.random() < 0.5:
            extra["allowed_domains"] = [ctx.recipient_domain]
        else:
            extra["allowed_domains"] = [
                d for d in _RECIPIENT_DOMAIN_POOL if d != ctx.recipient_domain
            ][:2]
    elif kind is PolicyPredicateKind.DATA_RESIDENCY_REGION:
        if rng.random() < 0.5:
            extra["allowed_regions"] = [ctx.resource_region]
        else:
            extra["allowed_regions"] = [r for r in _REGION_POOL if r != ctx.resource_region][:2]
    elif kind is PolicyPredicateKind.FORBID_PII_FIELD_EXPORT:
        if ctx.touched_pii_fields and rng.random() < 0.5:
            extra["pii_fields"] = list(ctx.touched_pii_fields)
        else:
            remaining = [f for f in _PII_FIELD_POOL if f not in ctx.touched_pii_fields]
            extra["pii_fields"] = remaining[:2] or list(_PII_FIELD_POOL[:2])
    return PolicyPredicate(id=predicate_id, kind=kind, paraphrase_index=paraphrase_index, **extra)


def _sample_sequence(rng: random.Random) -> tuple[int, SequencePattern]:
    if rng.random() >= 0.2:
        return 0, SequencePattern.NONE
    length = rng.randint(1, 5)
    if rng.random() < 0.3:
        return length, rng.choice(_ATTACK_SEQUENCE_LIST)
    return length, rng.choice(_BENIGN_SEQUENCE_PATTERNS)


def _sample_context_gaps(rng: random.Random) -> list[ContextGap]:
    if rng.random() >= 0.14:
        return [ContextGap.NONE]
    n_gaps = 2 if rng.random() < 0.2 else 1
    return list(rng.sample(_NON_NONE_GAPS, k=min(n_gaps, len(_NON_NONE_GAPS))))


def sample_scenario(rng: random.Random, family: ToolFamily, scenario_id: str) -> LatentScenario:
    """Draw one plausible :class:`LatentScenario` for ``family``, seeded by ``rng``."""
    tool = _choose_tool(rng, family)
    operation = tool.operation
    origin_result = _sample_action_origin(rng)
    origin, untrusted_present, untrusted_has_instruction, is_hard_negative = origin_result
    principal_roles, entitlements, delegated = _sample_scopes(rng, list(tool.required_scopes))
    effective_scopes = frozenset(entitlements) & frozenset(delegated)
    authority_before, authority_after = _sample_authority(rng, tool, operation, effective_scopes)
    destination_present, destination_relationship, destination_trust = _sample_destination(
        rng, tool, operation
    )
    resource_sensitivity = rng.choices(_SENSITIVITY_LEVELS, weights=_SENSITIVITY_WEIGHTS, k=1)[0]
    resource_reversible = rng.random() < (0.2 if operation is OperationKind.DELETE else 0.95)
    record_count = rng.randint(1, 500)
    stage = rng.choices(_STAGES, weights=_STAGE_WEIGHTS, k=1)[0]
    change_freeze = rng.random() < 0.1
    financial_amount = _sample_financial_amount(rng, family, tool)
    local_hour = rng.randint(0, 23)
    resource_region = rng.choice(_REGION_POOL)
    recipient_domain = (
        rng.choice(_RECIPIENT_DOMAIN_POOL)
        if destination_present
        and tool.is_communication
        and destination_relationship is not DestinationRelationship.LOOKALIKE
        else None
    )
    ticket_reference = f"TICKET-{rng.randint(1000, 9999)}" if rng.random() < 0.5 else None
    dry_run_performed = rng.random() < 0.5
    touched_pii_fields = rng.sample(_PII_FIELD_POOL, k=rng.randint(0, 2))
    policy_ctx = _PolicyContext(
        tool=tool,
        operation=operation,
        resource_sensitivity=resource_sensitivity,
        stage=stage,
        principal_roles=principal_roles,
        financial_amount=financial_amount,
        record_count=record_count,
        local_hour=local_hour,
        resource_region=resource_region,
        recipient_domain=recipient_domain,
        dry_run_performed=dry_run_performed,
        touched_pii_fields=touched_pii_fields,
    )
    policy_supplied, policy_predicates = _sample_policy_predicates(rng, policy_ctx)
    trajectory_length, sequence_pattern = _sample_sequence(rng)
    context_gaps = _sample_context_gaps(rng)
    authorization_basis = rng.choices(tuple(AuthorizationBasis), weights=(0.6, 0.3, 0.1), k=1)[0]

    untrusted_origins = (ActionOrigin.INJECTED_INSTRUCTION, ActionOrigin.COMPROMISED_TOOL_SCHEMA)
    is_adversarial = origin in untrusted_origins or sequence_pattern in ATTACK_SEQUENCE_PATTERNS
    other_tiers = (DifficultyTier.EASY, DifficultyTier.MEDIUM, DifficultyTier.HARD)
    difficulty = DifficultyTier.ADVERSARIAL if is_adversarial else rng.choice(other_tiers)

    family_id = f"{family.value}:{tool.name}"
    return LatentScenario(
        scenario_id=scenario_id,
        family_id=family_id,
        template_lineage=[f"{family_id}#{scenario_id}"],
        tool=tool,
        operation=operation,
        principal_roles=principal_roles,
        principal_entitlements=entitlements,
        agent_delegated_scopes=delegated,
        required_scopes=list(tool.required_scopes),
        authorization_basis=authorization_basis,
        action_origin=origin,
        resource_sensitivity=resource_sensitivity,
        resource_reversible=resource_reversible,
        record_count=record_count,
        destination_present=destination_present,
        destination_relationship=destination_relationship,
        destination_trust=destination_trust,
        stage=stage,
        change_freeze=change_freeze,
        local_hour=local_hour,
        resource_region=resource_region,
        financial_amount=financial_amount,
        financial_material_threshold=100.0,
        untrusted_content_present=untrusted_present,
        untrusted_content_contains_instruction=untrusted_has_instruction,
        authority_before=authority_before,
        authority_after=authority_after,
        recipient_domain=recipient_domain,
        ticket_reference=ticket_reference,
        dry_run_performed=dry_run_performed,
        touched_pii_fields=touched_pii_fields,
        policy_predicates=policy_predicates,
        policy_supplied=policy_supplied,
        sequence_pattern=sequence_pattern,
        trajectory_length=trajectory_length,
        context_gaps=context_gaps,
        difficulty=difficulty,
        is_benign_hard_negative=is_hard_negative,
        notes="",
    )


def iter_scenarios(
    rng: random.Random, *, families: tuple[ToolFamily, ...] = tuple(ToolFamily), n_per_family: int
) -> list[LatentScenario]:
    """Draw ``n_per_family`` scenarios for each of ``families``, in family order."""
    scenarios: list[LatentScenario] = []
    for family in families:
        for i in range(n_per_family):
            scenario_id = f"{family.value}-{i:05d}"
            scenarios.append(sample_scenario(rng, family, scenario_id))
    return scenarios
