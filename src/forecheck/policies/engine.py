"""The deterministic policy evaluator.

Everything in this module is a pure function of its arguments: a :class:`PolicyBundle`,
a :class:`~forecheck.contracts.ClassifyResponse` and an optional
:class:`~forecheck.contracts.ActionContext`. No I/O, no clock, no randomness. The same
three inputs always produce the same :class:`~forecheck.contracts.PolicyDecision`.

Three-valued logic. A leaf predicate (a ``score`` or ``fact`` check) evaluates to
``TRUE``, ``FALSE`` or ``UNKNOWN``. ``UNKNOWN`` arises from an abstained dimension, a
dimension the classification never scored, or a fact that could not be derived
(including the case where no context was supplied at all). ``all``/``any``/``not``
propagate ``UNKNOWN`` using standard Kleene logic. A rule's ``when`` tree is resolved to
a concrete boolean only once, at the top, using :class:`~forecheck.policies.dsl.UnknownAs`:
``worst_case`` (the default) resolves ``UNKNOWN`` in whichever direction is more
restrictive for that rule's own decision, so uncertainty can never make the outcome
*less* safe.
"""

from __future__ import annotations

import enum

from forecheck.contracts import (
    MUTATING_OPERATIONS,
    ActionContext,
    CalibrationMethod,
    ClassifyResponse,
    Decision,
    DimensionScore,
    Obligation,
    ObligationKind,
    OperationKind,
    PolicyDecision,
    RuleKind,
    RuleMatch,
)
from forecheck.policies.base import PolicyEngineBase
from forecheck.policies.dsl import Condition, FactValue, PolicyBundle, Rule, UnknownAs

__all__ = [
    "FACT_NAMES",
    "DeterministicPolicyEngine",
    "FactTable",
    "combine_matched_rules",
    "derive_facts",
]

FactTable = dict[str, FactValue | list[str] | None]

FACT_NAMES: frozenset[str] = frozenset(
    {
        "operation_is_mutating",
        "operation",
        "max_sensitivity",
        "stage",
        "change_freeze",
        "destination_relationship",
        "destination_present",
        "has_untrusted_content",
        "authorization_explicit",
        "principal_type",
        "agent_has_scope_for_tool",
        "financial_amount",
        "financial_currency",
        "record_count_estimate",
        "trajectory_length",
        "tool_family",
        "tool_name",
        "mfa_satisfied",
        "resource_kinds",
    }
)
"""Every fact name a bundle's ``fact`` predicates may reference. The loader rejects any
bundle that names a fact outside this set at load time."""

_OPERATION_SEVERITY: dict[OperationKind, int] = {
    OperationKind.READ: 0,
    OperationKind.LIST: 0,
    OperationKind.CREATE: 1,
    OperationKind.UPDATE: 2,
    OperationKind.EXECUTE: 3,
    OperationKind.TRANSFER: 4,
    OperationKind.GRANT: 5,
    OperationKind.REVOKE: 5,
    OperationKind.DELETE: 6,
}

_DECISION_RANK: dict[Decision, int] = {
    Decision.ALLOW: 0,
    Decision.REVIEW: 1,
    Decision.DENY: 2,
}


class _Tri(enum.Enum):
    """A three-valued logic value used only while walking a condition tree."""

    TRUE = "true"
    FALSE = "false"
    UNKNOWN = "unknown"

    @classmethod
    def of(cls, value: bool) -> _Tri:
        return cls.TRUE if value else cls.FALSE


def _agent_has_scope_for_tool(context: ActionContext) -> bool | None:
    """Conservative scope check.

    The tool's *required* scopes are not known at serve time, so this can never assert
    "yes, covered": only that no scope at all was delegated (``False``), that a wildcard
    scope was delegated (``True``), or that we genuinely cannot tell (``None``, treated
    as unknown by the bundle's ``unknown_as`` policy rather than optimistically as
    ``True``).
    """
    scopes = context.agent.delegated_scopes
    if not scopes:
        return False
    if "*" in scopes:
        return True
    return None


def _most_severe_operation(context: ActionContext) -> OperationKind | None:
    if not context.resources:
        return None
    return max(
        (resource.operation for resource in context.resources),
        key=lambda op: _OPERATION_SEVERITY[op],
    )


def _max_record_count_estimate(context: ActionContext) -> int | None:
    estimates = [
        resource.record_count_estimate
        for resource in context.resources
        if resource.record_count_estimate is not None
    ]
    return max(estimates) if estimates else None


def derive_facts(context: ActionContext | None) -> FactTable:
    """Build the fact table a bundle's ``fact`` predicates read from.

    Returns an empty table when ``context`` is ``None``, so every fact predicate looks
    up ``None`` and is treated as unknown rather than false. A fact present in the table
    with a real value of ``False``, ``0`` or ``[]`` is a known negative, not unknown.
    """
    if context is None:
        return {}
    operation = _most_severe_operation(context)
    return {
        "operation_is_mutating": (
            operation in MUTATING_OPERATIONS if operation is not None else None
        ),
        "operation": operation.value if operation is not None else None,
        "max_sensitivity": (
            context.max_sensitivity.value if context.max_sensitivity is not None else None
        ),
        "stage": context.environment.stage.value,
        "change_freeze": context.environment.change_freeze,
        "destination_relationship": (
            context.destination.relationship.value if context.destination is not None else None
        ),
        "destination_present": context.destination is not None,
        "has_untrusted_content": context.has_untrusted_content,
        "authorization_explicit": context.objective.authorization_explicit,
        "principal_type": context.principal.type.value,
        "agent_has_scope_for_tool": _agent_has_scope_for_tool(context),
        "financial_amount": context.financial.amount if context.financial is not None else None,
        "financial_currency": (
            context.financial.currency if context.financial is not None else None
        ),
        "record_count_estimate": _max_record_count_estimate(context),
        "trajectory_length": len(context.trajectory),
        "tool_family": (
            context.proposed_action.tool_family.value
            if context.proposed_action.tool_family is not None
            else None
        ),
        "tool_name": context.proposed_action.tool_name,
        "mfa_satisfied": context.principal.mfa_satisfied,
        "resource_kinds": sorted({resource.kind.value for resource in context.resources}),
    }


def _score_value(score: DimensionScore | None, *, use_raw: bool) -> float | None:
    if score is None or score.abstained:
        return None
    return score.raw_score if use_raw else score.probability


def _compare_score(value: float, condition: Condition) -> bool:
    if condition.gte is not None and not value >= condition.gte:
        return False
    if condition.gt is not None and not value > condition.gt:
        return False
    if condition.lte is not None and not value <= condition.lte:
        return False
    return not (condition.lt is not None and not value < condition.lt)


def _compare_fact(actual: FactValue | list[str], condition: Condition) -> bool:
    if condition.is_ is not None:
        if isinstance(actual, list):
            return condition.is_ in actual
        return actual == condition.is_
    if condition.in_ is not None:
        if isinstance(actual, list):
            return any(v in condition.in_ for v in actual)
        return actual in condition.in_
    if condition.gte is not None or condition.gt is not None:
        numeric = float(actual)  # type: ignore[arg-type]
        if condition.gte is not None and not numeric >= condition.gte:
            return False
        return not (condition.gt is not None and not numeric > condition.gt)
    numeric = float(actual)  # type: ignore[arg-type]
    if condition.lte is not None and not numeric <= condition.lte:
        return False
    return not (condition.lt is not None and not numeric < condition.lt)


def _evaluate_leaf(
    condition: Condition,
    classification: ClassifyResponse,
    facts: FactTable,
    *,
    use_raw_scores: bool,
) -> _Tri:
    if condition.score is not None:
        dimension_score = classification.by_dimension().get(condition.score)
        value = _score_value(dimension_score, use_raw=use_raw_scores)
        if value is None:
            return _Tri.UNKNOWN
        return _Tri.of(_compare_score(value, condition))
    if condition.fact is not None:
        actual = facts.get(condition.fact)
        if actual is None:
            return _Tri.UNKNOWN
        return _Tri.of(_compare_fact(actual, condition))
    raise ValueError("condition leaf must set either score or fact")


def _evaluate_condition(
    condition: Condition,
    classification: ClassifyResponse,
    facts: FactTable,
    *,
    use_raw_scores: bool,
) -> _Tri:
    if condition.all_ is not None:
        results = [
            _evaluate_condition(child, classification, facts, use_raw_scores=use_raw_scores)
            for child in condition.all_
        ]
        if any(r is _Tri.FALSE for r in results):
            return _Tri.FALSE
        if any(r is _Tri.UNKNOWN for r in results):
            return _Tri.UNKNOWN
        return _Tri.TRUE
    if condition.any_ is not None:
        results = [
            _evaluate_condition(child, classification, facts, use_raw_scores=use_raw_scores)
            for child in condition.any_
        ]
        if any(r is _Tri.TRUE for r in results):
            return _Tri.TRUE
        if any(r is _Tri.UNKNOWN for r in results):
            return _Tri.UNKNOWN
        return _Tri.FALSE
    if condition.not_ is not None:
        inner = _evaluate_condition(
            condition.not_, classification, facts, use_raw_scores=use_raw_scores
        )
        if inner is _Tri.UNKNOWN:
            return _Tri.UNKNOWN
        return _Tri.FALSE if inner is _Tri.TRUE else _Tri.TRUE
    return _evaluate_leaf(condition, classification, facts, use_raw_scores=use_raw_scores)


def _resolve_tri(tri: _Tri, decision: Decision, unknown_as: UnknownAs) -> bool:
    if tri is not _Tri.UNKNOWN:
        return tri is _Tri.TRUE
    if unknown_as is UnknownAs.WORST_CASE:
        return decision is not Decision.ALLOW
    return False


def _collect_leaves(condition: Condition) -> list[Condition]:
    if condition.all_ is not None:
        return [leaf for child in condition.all_ for leaf in _collect_leaves(child)]
    if condition.any_ is not None:
        return [leaf for child in condition.any_ for leaf in _collect_leaves(child)]
    if condition.not_ is not None:
        return _collect_leaves(condition.not_)
    return [condition]


def _describe_threshold(condition: Condition) -> str:
    parts: list[str] = []
    if condition.gte is not None:
        parts.append(f"gte {condition.gte}")
    if condition.gt is not None:
        parts.append(f"gt {condition.gt}")
    if condition.lte is not None:
        parts.append(f"lte {condition.lte}")
    if condition.lt is not None:
        parts.append(f"lt {condition.lt}")
    if condition.is_ is not None:
        parts.append(f"is {condition.is_}")
    if condition.in_ is not None:
        parts.append(f"in {condition.in_}")
    return ", ".join(parts)


def _matched_on(
    rule: Rule,
    classification: ClassifyResponse,
    facts: FactTable,
    *,
    use_raw_scores: bool,
) -> dict[str, str]:
    matched_on: dict[str, str] = {}
    seen: dict[str, int] = {}
    for leaf in _collect_leaves(rule.when):
        name = str(leaf.score) if leaf.score is not None else str(leaf.fact)
        seen[name] = seen.get(name, 0) + 1
        key = name if seen[name] == 1 else f"{name}#{seen[name]}"
        if leaf.score is not None:
            value = _score_value(
                classification.by_dimension().get(leaf.score), use_raw=use_raw_scores
            )
            matched_on[key] = "unknown" if value is None else f"{value:.4f}"
        else:
            actual = facts.get(str(leaf.fact))
            matched_on[key] = "unknown" if actual is None else str(actual)
        matched_on[f"{key}.threshold"] = _describe_threshold(leaf)
    return matched_on


def combine_matched_rules(matches: list[RuleMatch], default_decision: Decision) -> Decision:
    """Combine already-fired rules into a single decision.

    This is the entire combination policy, and it is deliberately the same function
    used live and in a "replay" that only has the ``matched_rules`` a
    :class:`~forecheck.contracts.PolicyDecision` already carries: most-restrictive-wins,
    an ``allow_override`` rule may force ``ALLOW`` when nothing else fired is ``hard``,
    and it can never do so once a ``hard`` rule has fired.
    """
    if not matches:
        return default_decision
    hard_fired = any(match.hard for match in matches)
    standard = [match for match in matches if match.kind is not RuleKind.ALLOW_OVERRIDE]
    override_fired = len(standard) != len(matches)
    if not standard:
        return Decision.ALLOW
    base = max((match.decision for match in standard), key=lambda d: _DECISION_RANK[d])
    if override_fired and not hard_fired:
        return Decision.ALLOW
    return base


def _aggregate_obligations(matches: list[RuleMatch]) -> list[Obligation]:
    seen: set[tuple[ObligationKind, str | None]] = set()
    obligations: list[Obligation] = []
    for match in matches:
        for obligation in match.obligations:
            key = (obligation.kind, obligation.detail)
            if key not in seen:
                seen.add(key)
                obligations.append(obligation)
    return obligations


_UNCALIBRATED_WARNING_DETAIL = (
    "classification is uncalibrated; score thresholds were evaluated against raw "
    "scores because the bundle sets allow_uncalibrated: true"
)


class DeterministicPolicyEngine(PolicyEngineBase):
    """The one :class:`~forecheck.policies.base.PolicyEngine` implementation.

    Constructed with an already-loaded, already-validated :class:`PolicyBundle` and its
    precomputed hash; see :mod:`forecheck.policies.loader` for how bundles get here.
    """

    def __init__(self, bundle: PolicyBundle, bundle_hash: str) -> None:
        self._bundle = bundle
        self._bundle_hash = bundle_hash

    @property
    def bundle_id(self) -> str:
        return self._bundle.bundle_id

    @property
    def bundle_hash(self) -> str:
        return self._bundle_hash

    @property
    def default_decision(self) -> Decision:
        return self._bundle.default_decision

    @property
    def bundle(self) -> PolicyBundle:
        return self._bundle

    def evaluate(
        self, classification: ClassifyResponse, context: ActionContext | None = None
    ) -> PolicyDecision:
        bundle = self._bundle
        uncalibrated = classification.calibration.method is CalibrationMethod.NONE
        if uncalibrated and not bundle.allow_uncalibrated:
            return PolicyDecision(
                request_id=classification.request_id,
                decision=bundle.uncalibrated_decision,
                matched_rules=[],
                obligations=[],
                policy_bundle_id=bundle.bundle_id,
                policy_bundle_hash=self._bundle_hash,
                classification=classification,
            )
        use_raw_scores = uncalibrated and bundle.allow_uncalibrated
        facts = derive_facts(context)
        matches: list[RuleMatch] = []
        for rule in bundle.rules:
            tri = _evaluate_condition(
                rule.when, classification, facts, use_raw_scores=use_raw_scores
            )
            if not _resolve_tri(tri, rule.decision, bundle.unknown_as):
                continue
            matches.append(
                RuleMatch(
                    rule_id=rule.id,
                    decision=rule.decision,
                    description=rule.description,
                    matched_on=_matched_on(
                        rule, classification, facts, use_raw_scores=use_raw_scores
                    ),
                    obligations=[Obligation(kind=kind) for kind in rule.obligations],
                    hard=rule.hard,
                    kind=rule.kind,
                )
            )
        decision = combine_matched_rules(matches, bundle.default_decision)
        obligations = _aggregate_obligations(matches)
        if use_raw_scores:
            obligations = [
                *obligations,
                Obligation(
                    kind=ObligationKind.LOG_TO_AUDIT_SINK,
                    detail=_UNCALIBRATED_WARNING_DETAIL,
                ),
            ]
        return PolicyDecision(
            request_id=classification.request_id,
            decision=decision,
            matched_rules=matches,
            obligations=obligations,
            policy_bundle_id=bundle.bundle_id,
            policy_bundle_hash=self._bundle_hash,
            classification=classification,
        )
