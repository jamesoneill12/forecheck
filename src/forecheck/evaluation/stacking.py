"""Multi-policy stacking evaluation.

Measures the difference between three ways of combining K policies over the same
probability vector: ``independent`` evaluates each of the first k policies on its
own and takes the most severe of the k final decisions (OR-of-guards); ``joint``
merges the first k policies' rules into one bundle and evaluates it once with the
forecheck engine's own combination rule
(:func:`forecheck.policies.engine.combine_matched_rules`); ``expected_cost_joint``
evaluates that same merged bundle in ``decision_mode: expected_cost``, using the
covered dimensions' probabilities jointly rather than per-rule thresholds. See
``tests/evaluation/test_stacking.py`` for the exact equivalence ``joint`` guarantees
versus ``independent`` for rule sets with no hard/allow_override rules, its
documented limit once those are mixed in, and the property test showing
``expected_cost_joint``'s false-positive rate stays bounded as k grows where
``independent``'s does not.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from forecheck.contracts import (
    META_DIMENSIONS,
    Decision,
    Example,
    LabelValue,
    RiskDimension,
)
from forecheck.evaluation.decisions import DEFAULT_COST_MATRIX, CostMatrix, decision_metrics
from forecheck.policies.dsl import (
    Condition,
    DecisionMode,
    PolicyBundle,
    Rule,
    RuleKind,
    UnknownAs,
)
from forecheck.policies.engine import DeterministicPolicyEngine, combine_matched_rules
from forecheck.policies.loader import hash_bundle
from forecheck.version import POLICY_DSL_VERSION

__all__ = [
    "StackingReport",
    "StackingRow",
    "merge_bundles",
    "stacking_report",
    "synthetic_dimension_policies",
]

Strategy = Literal["independent", "joint", "expected_cost_joint"]

_DECISION_RANK: dict[Decision, int] = {Decision.ALLOW: 0, Decision.REVIEW: 1, Decision.DENY: 2}


class StackingRow(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    k: int = Field(ge=1)
    strategy: Strategy
    policy_ids: list[str]
    n: int
    n_covered_benign: int
    n_covered_risky: int
    false_positive_rate: float | None
    false_negative_rate: float | None
    review_rate: float | None
    mean_risk_weighted_cost: float | None


class StackingReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rows: list[StackingRow]

    def to_markdown(self) -> str:
        lines = ["## Multi-policy stacking", ""]
        lines.append(
            "Independent = OR across the first k policies evaluated separately "
            "(each guard alone decides, the stack takes the most severe). "
            "Joint = the first k policies' rules merged into one bundle and "
            "evaluated once by the forecheck policy engine, in threshold mode. "
            "expected_cost_joint = the same merged bundle evaluated in "
            "decision_mode: expected_cost, using the joint probability vector "
            "instead of per-rule thresholds."
        )
        lines.append("")
        lines.append(
            "| k | strategy | policies | n | benign_covered | risky_covered | fpr | fnr | "
            "review_rate | mean_cost |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|---|")
        for row in self.rows:
            lines.append(
                f"| {row.k} | {row.strategy} | {', '.join(row.policy_ids)} | {row.n} | "
                f"{row.n_covered_benign} | {row.n_covered_risky} | "
                f"{_fmt(row.false_positive_rate)} | {_fmt(row.false_negative_rate)} | "
                f"{_fmt(row.review_rate)} | {_fmt(row.mean_risk_weighted_cost)} |"
            )
        return "\n".join(lines) + "\n"


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def synthetic_dimension_policies(
    *,
    thresholds: Mapping[RiskDimension, float] | None = None,
    default_threshold: float = 0.5,
) -> list[PolicyBundle]:
    """Build 11 single-dimension policies, one per :class:`RiskDimension`.

    Uses ``thresholds[dimension]`` when supplied, else ``default_threshold``.
    Dimensions in :data:`META_DIMENSIONS` route to REVIEW rather than DENY, since
    they are not derivable from the latent scenario alone.
    """
    thresholds = thresholds or {}
    policies: list[PolicyBundle] = []
    for dimension in RiskDimension:
        tau = thresholds.get(dimension, default_threshold)
        decision = Decision.REVIEW if dimension in META_DIMENSIONS else Decision.DENY
        rule = Rule(
            id=f"stack_{dimension.value}",
            description=f"Synthetic single-dimension policy: {dimension.value} >= {tau:.4f}.",
            decision=decision,
            when=Condition(score=dimension, gte=tau),
            hard=False,
            kind=RuleKind.STANDARD,
        )
        policies.append(
            PolicyBundle(
                bundle_id=f"synthetic-{dimension.value}",
                version=1,
                dsl_version=POLICY_DSL_VERSION,
                description=f"Synthetic single-dimension guard on {dimension.value}.",
                default_decision=Decision.ALLOW,
                uncalibrated_decision=Decision.REVIEW,
                allow_uncalibrated=True,
                unknown_as=UnknownAs.WORST_CASE,
                rules=[rule],
            )
        )
    return policies


def _covered_dimensions(condition: Condition, into: set[RiskDimension]) -> None:
    if condition.all_ is not None:
        for child in condition.all_:
            _covered_dimensions(child, into)
        return
    if condition.any_ is not None:
        for child in condition.any_:
            _covered_dimensions(child, into)
        return
    if condition.not_ is not None:
        _covered_dimensions(condition.not_, into)
        return
    if condition.score is not None:
        into.add(condition.score)


def _bundle_covered_dimensions(bundle: PolicyBundle) -> frozenset[RiskDimension]:
    covered: set[RiskDimension] = set()
    for rule in bundle.rules:
        _covered_dimensions(rule.when, covered)
    return frozenset(covered)


def merge_bundles(bundles: Sequence[PolicyBundle], bundle_id: str) -> PolicyBundle:
    """Union the rules of ``bundles`` into one bundle, deduplicated by rule id.

    Default/uncalibrated decisions are the most severe among the inputs', so
    "no rule fired" resolves the same way it would under independent stacking.
    """
    seen_ids: set[str] = set()
    merged_rules: list[Rule] = []
    for bundle in bundles:
        for rule in bundle.rules:
            if rule.id in seen_ids:
                continue
            seen_ids.add(rule.id)
            merged_rules.append(rule)
    default_decision = max((b.default_decision for b in bundles), key=lambda d: _DECISION_RANK[d])
    uncalibrated_decision = max(
        (b.uncalibrated_decision for b in bundles), key=lambda d: _DECISION_RANK[d]
    )
    names = ", ".join(b.bundle_id for b in bundles)
    return PolicyBundle(
        bundle_id=bundle_id,
        version=1,
        dsl_version=POLICY_DSL_VERSION,
        description=f"Joint stack of {len(bundles)} polic{'y' if len(bundles) == 1 else 'ies'}: "
        f"{names}.",
        default_decision=default_decision,
        uncalibrated_decision=uncalibrated_decision,
        allow_uncalibrated=True,
        unknown_as=UnknownAs.WORST_CASE,
        rules=merged_rules,
    )


class _IndependentStackEngine:
    """Evaluates each sub-bundle on its own; each guard's hard/override logic
    applies only within that guard, never across guards."""

    def __init__(self, bundles: Sequence[PolicyBundle]) -> None:
        self._engines = [DeterministicPolicyEngine(b, hash_bundle(b)) for b in bundles]

    @property
    def bundle_id(self) -> str:
        return "independent-stack"

    @property
    def bundle_hash(self) -> str:
        return "|".join(engine.bundle_hash for engine in self._engines)

    @property
    def default_decision(self) -> Decision:
        return Decision.ALLOW

    def evaluate(self, classification: object, context: object = None) -> object:
        from forecheck.contracts import PolicyDecision, RuleMatch

        sub_decisions = [engine.evaluate(classification, context) for engine in self._engines]  # type: ignore[arg-type]
        matches = [
            RuleMatch(
                rule_id=engine.bundle_id,
                decision=decision.decision,
                description=f"final decision of policy {engine.bundle_id!r}",
                hard=False,
                kind=RuleKind.STANDARD,
            )
            for engine, decision in zip(self._engines, sub_decisions, strict=True)
        ]
        decision = combine_matched_rules(matches, Decision.ALLOW)
        return PolicyDecision(
            decision=decision,
            matched_rules=[m for d in sub_decisions for m in d.matched_rules],
            obligations=[o for d in sub_decisions for o in d.obligations],
            policy_bundle_id=self.bundle_id,
            policy_bundle_hash=self.bundle_hash,
            classification=classification,
        )


def _all_covered_benign(example: Example, covered: frozenset[RiskDimension]) -> bool:
    return all(
        example.labels.values[dimension] in (LabelValue.NO, LabelValue.NOT_APPLICABLE)
        for dimension in covered
    )


def _any_covered_risky(example: Example, covered: frozenset[RiskDimension]) -> bool:
    return any(example.labels.values[dimension] is LabelValue.YES for dimension in covered)


def _stack_row(
    k: int,
    strategy: Strategy,
    subset: Sequence[PolicyBundle],
    engine: object,
    responses: Sequence[object],
    examples: Sequence[Example],
    cost_matrix: CostMatrix,
) -> StackingRow:
    covered = frozenset().union(*(_bundle_covered_dimensions(b) for b in subset))
    decisions = [
        engine.evaluate(r, e.context).decision  # type: ignore[attr-defined]
        for r, e in zip(responses, examples, strict=True)
    ]
    n = len(examples)
    n_review = sum(1 for d in decisions if d is Decision.REVIEW)
    benign_idx = [i for i, e in enumerate(examples) if _all_covered_benign(e, covered)]
    risky_idx = [i for i, e in enumerate(examples) if _any_covered_risky(e, covered)]
    fpr = (
        sum(1 for i in benign_idx if decisions[i] is not Decision.ALLOW) / len(benign_idx)
        if benign_idx
        else None
    )
    fnr = (
        sum(1 for i in risky_idx if decisions[i] is Decision.ALLOW) / len(risky_idx)
        if risky_idx
        else None
    )
    metrics = decision_metrics(engine, responses, examples, cost_matrix=cost_matrix)  # type: ignore[arg-type]
    return StackingRow(
        k=k,
        strategy=strategy,
        policy_ids=[b.bundle_id for b in subset],
        n=n,
        n_covered_benign=len(benign_idx),
        n_covered_risky=len(risky_idx),
        false_positive_rate=fpr,
        false_negative_rate=fnr,
        review_rate=n_review / n if n else None,
        mean_risk_weighted_cost=metrics.mean_risk_weighted_cost,
    )


def stacking_report(
    examples: Sequence[Example],
    responses: Sequence[object],
    policies: Sequence[PolicyBundle],
    *,
    cost_matrix: CostMatrix = DEFAULT_COST_MATRIX,
) -> StackingReport:
    """Compute independent-stack and joint-stack decision metrics for k = 1..K.

    ``responses`` must be positionally paired with ``examples``, as in
    :func:`forecheck.evaluation.decisions.decision_metrics`.
    """
    if len(examples) != len(responses):
        raise ValueError("examples and responses must be the same length")
    if not policies:
        raise ValueError("at least one policy is required for a stacking report")
    rows: list[StackingRow] = []
    for k in range(1, len(policies) + 1):
        subset = policies[:k]
        independent_engine = _IndependentStackEngine(subset)
        rows.append(
            _stack_row(
                k, "independent", subset, independent_engine, responses, examples, cost_matrix
            )
        )
        joint_bundle = merge_bundles(subset, f"joint-stack-k{k}")
        joint_engine = DeterministicPolicyEngine(joint_bundle, hash_bundle(joint_bundle))
        rows.append(_stack_row(k, "joint", subset, joint_engine, responses, examples, cost_matrix))
        expected_cost_bundle = joint_bundle.model_copy(
            update={
                "bundle_id": f"expected-cost-joint-stack-k{k}",
                "decision_mode": DecisionMode.EXPECTED_COST,
            }
        )
        expected_cost_engine = DeterministicPolicyEngine(
            expected_cost_bundle, hash_bundle(expected_cost_bundle)
        )
        rows.append(
            _stack_row(
                k,
                "expected_cost_joint",
                subset,
                expected_cost_engine,
                responses,
                examples,
                cost_matrix,
            )
        )
    return StackingReport(rows=rows)
