"""Samplers that draw plausible :class:`LatentScenario` instances for a tool family.

Sampling is intentionally biased toward benign traffic: most drawn scenarios should be
unremarkable, low-risk tool calls, with a minority carrying one or more risk signals.
This keeps the derived label distribution realistic (mostly negative, some positives on
each dimension) rather than adversarial-only.
"""

from __future__ import annotations

import random

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
_ATTACK_SEQUENCE_LIST: tuple[SequencePattern, ...] = tuple(ATTACK_SEQUENCE_PATTERNS)
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


def _sample_policy_predicates(
    rng: random.Random,
    tool: ToolSpec,
    operation: OperationKind,
    resource_sensitivity: Sensitivity,
    stage: Stage,
    principal_roles: list[str],
    financial_amount: float,
) -> tuple[bool, list[PolicyPredicate]]:
    if rng.random() >= 0.28:
        return False, []
    n_predicates = rng.randint(1, 2)
    predicates: list[PolicyPredicate] = []
    for i in range(n_predicates):
        kind = rng.choice(_POLICY_KINDS)
        predicate = _build_predicate(
            rng,
            i,
            kind,
            tool,
            operation,
            resource_sensitivity,
            stage,
            principal_roles,
            financial_amount,
        )
        predicates.append(predicate)
    return True, predicates


def _build_predicate(
    rng: random.Random,
    index: int,
    kind: PolicyPredicateKind,
    tool: ToolSpec,
    operation: OperationKind,
    resource_sensitivity: Sensitivity,
    stage: Stage,
    principal_roles: list[str],
    financial_amount: float,
) -> PolicyPredicate:
    predicate_id = f"policy-{index}"
    if kind is PolicyPredicateKind.FORBID_TOOL:
        name = tool.name if rng.random() < 0.25 else f"other.{tool.name}"
        return PolicyPredicate(id=predicate_id, kind=kind, tool_name=name)
    if kind is PolicyPredicateKind.FORBID_OPERATION_ON_SENSITIVITY:
        op = operation if rng.random() < 0.5 else OperationKind.EXECUTE
        min_sensitivity = resource_sensitivity if rng.random() < 0.5 else Sensitivity.SECRET
        return PolicyPredicate(
            id=predicate_id, kind=kind, operation=op, min_sensitivity=min_sensitivity
        )
    if kind is PolicyPredicateKind.FORBID_EXTERNAL_DESTINATION:
        return PolicyPredicate(id=predicate_id, kind=kind)
    if kind is PolicyPredicateKind.FORBID_IN_STAGE:
        target_stage = stage if rng.random() < 0.3 else Stage.DEVELOPMENT
        return PolicyPredicate(id=predicate_id, kind=kind, stage=target_stage)
    if kind is PolicyPredicateKind.REQUIRE_EXPLICIT_AUTHORIZATION:
        return PolicyPredicate(id=predicate_id, kind=kind)
    if kind is PolicyPredicateKind.MAX_FINANCIAL_AMOUNT:
        threshold = financial_amount / 2 if rng.random() < 0.5 else financial_amount + 1000.0
        return PolicyPredicate(id=predicate_id, kind=kind, max_amount=max(threshold, 0.0))
    if kind is PolicyPredicateKind.FORBID_ROLE:
        role = rng.choice(principal_roles) if rng.random() < 0.3 else "restricted_role"
        return PolicyPredicate(id=predicate_id, kind=kind, role=role)
    return PolicyPredicate(id=predicate_id, kind=kind)


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
    policy_supplied, policy_predicates = _sample_policy_predicates(
        rng, tool, operation, resource_sensitivity, stage, principal_roles, financial_amount
    )
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
        template_lineage=[family_id],
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
        financial_amount=financial_amount,
        financial_material_threshold=100.0,
        untrusted_content_present=untrusted_present,
        untrusted_content_contains_instruction=untrusted_has_instruction,
        authority_before=authority_before,
        authority_after=authority_after,
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
