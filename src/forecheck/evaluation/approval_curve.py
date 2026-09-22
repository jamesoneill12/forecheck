"""Approval-elimination curve.

See ``docs/evaluation/approval-elimination.md`` for the metric spec. That doc leaves
the exact per-example decision-relevant score unspecified (its §4, first open
question); this implementation uses ``expected_costs(bundle, response).allow`` — the
same "expected cost of ALLOW" quantity ``decision_mode: expected_cost`` already
computes over a bundle's covered dimensions (``docs/policy-dsl.md`` §2.3) — as the
ranking score. Lower cost means the bundle's covered dimensions jointly look safer to
auto-allow. This is a deliberate choice among the doc's alternatives, not a gap: it
reuses the DSL's own notion of "cost of allowing", rather than a max-probability
heuristic, and applies regardless of whether the bundle's own ``decision_mode`` is
``threshold`` or ``expected_cost``.
"""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from math import sqrt
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict

from forecheck.contracts import Decision, Example, LabelValue, RiskDimension
from forecheck.policies.dsl import Condition, PolicyBundle
from forecheck.policies.engine import expected_costs

if TYPE_CHECKING:
    from forecheck.contracts import ClassifyResponse
    from forecheck.policies.engine import DeterministicPolicyEngine

__all__ = [
    "DEFAULT_BUDGETS",
    "ApprovalCurvePoint",
    "ApprovalElimination",
    "ApprovalOperatingPoint",
    "IncidentRateMode",
    "approval_elimination_curve",
    "bundle_covered_dimensions",
]

DEFAULT_BUDGETS: tuple[float, ...] = (0.001, 0.005, 0.01, 0.02, 0.05)

_WILSON_Z = 1.959963984540054  # 95% two-sided Wilson z-score


class IncidentRateMode(StrEnum):
    """How ``incident_rate(k)`` is estimated from the ``k`` lowest-score examples.

    ``PREFIX`` is the point estimate (fraction risky among the allowed prefix); it can
    be dominated by a single low-scored risky row at small ``k``. ``SMOOTHED`` instead
    uses the upper bound of a 95% Wilson score interval around that point estimate, so
    small, noisy prefixes are treated conservatively rather than being taken at face
    value.
    """

    PREFIX = "prefix"
    SMOOTHED = "smoothed"


class ApprovalCurvePoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    allow_fraction: float
    incident_rate: float | None


class ApprovalOperatingPoint(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    budget: float
    approvals_eliminated: float
    incident_rate: float | None
    review_fraction: float
    deny_fraction: float
    n_allow: int
    n_review: int
    n_deny: int


class ApprovalElimination(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    bundle_id: str
    covered_dimensions: list[RiskDimension]
    n: int
    base_incident_rate: float | None
    incident_rate_mode: IncidentRateMode = IncidentRateMode.PREFIX
    operating_points: list[ApprovalOperatingPoint]
    curve: list[ApprovalCurvePoint]
    target_base_rate: float | None = None
    effective_base_rate: float | None = None
    weights: list[float] | None = None
    reweighted_operating_points: list[ApprovalOperatingPoint] | None = None
    reweighted_curve: list[ApprovalCurvePoint] | None = None

    def to_markdown(self) -> str:
        lines = ["## Approval elimination", ""]
        lines.append(
            f"Bundle `{self.bundle_id}`, n={self.n}, "
            f"base incident rate={_fmt(self.base_incident_rate)}, "
            f"incident rate mode={self.incident_rate_mode.value}. "
            "Ranking score: expected cost of ALLOW over the bundle's covered "
            f"dimensions ({', '.join(d.value for d in self.covered_dimensions)})."
        )
        lines.append("")
        if self.target_base_rate is not None:
            lines.append(
                f"Reweighted to target base rate={_fmt(self.target_base_rate)} "
                f"(effective={_fmt(self.effective_base_rate)})."
            )
            lines.append("")
            lines.append("### Unweighted")
            lines.append("")
            lines.append(_operating_points_table(self.operating_points))
            lines.append("### Reweighted")
            lines.append("")
            lines.append(_operating_points_table(self.reweighted_operating_points or []))
        else:
            lines.append(_operating_points_table(self.operating_points))
        return "\n".join(lines) + "\n"


def _operating_points_table(points: Sequence[ApprovalOperatingPoint]) -> str:
    lines = ["| budget | approvals eliminated | incident rate | review rate | deny rate |"]
    lines.append("|---|---|---|---|---|")
    for point in points:
        lines.append(
            f"| {point.budget:.3%} | {_fmt(point.approvals_eliminated)} | "
            f"{_fmt(point.incident_rate)} | {_fmt(point.review_fraction)} | "
            f"{_fmt(point.deny_fraction)} |"
        )
    return "\n".join(lines) + "\n"


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def _collect_score_dimensions(condition: Condition, into: set[RiskDimension]) -> None:
    if condition.all_ is not None:
        for child in condition.all_:
            _collect_score_dimensions(child, into)
        return
    if condition.any_ is not None:
        for child in condition.any_:
            _collect_score_dimensions(child, into)
        return
    if condition.not_ is not None:
        _collect_score_dimensions(condition.not_, into)
        return
    if condition.score is not None:
        into.add(condition.score)


def bundle_covered_dimensions(bundle: PolicyBundle) -> frozenset[RiskDimension]:
    """Every :class:`RiskDimension` any of ``bundle``'s rules reference via a ``score`` leaf."""
    covered: set[RiskDimension] = set()
    for rule in bundle.rules:
        _collect_score_dimensions(rule.when, covered)
    return frozenset(covered)


def _is_risky(example: Example, covered: frozenset[RiskDimension]) -> bool:
    return any(example.labels.values[dimension] is LabelValue.YES for dimension in covered)


def _empty_result(
    bundle_id: str,
    covered: frozenset[RiskDimension],
    budgets: Sequence[float],
    incident_rate_mode: IncidentRateMode,
) -> ApprovalElimination:
    empty_points = [
        ApprovalOperatingPoint(
            budget=budget,
            approvals_eliminated=0.0,
            incident_rate=None,
            review_fraction=0.0,
            deny_fraction=0.0,
            n_allow=0,
            n_review=0,
            n_deny=0,
        )
        for budget in budgets
    ]
    return ApprovalElimination(
        bundle_id=bundle_id,
        covered_dimensions=sorted(covered),
        n=0,
        base_incident_rate=None,
        incident_rate_mode=incident_rate_mode,
        operating_points=empty_points,
        curve=[],
    )


def _wilson_upper_bound(p: float, n: float, z: float = _WILSON_Z) -> float:
    """Upper bound of a two-sided Wilson score interval for proportion ``p`` over ``n`` trials."""
    if n <= 0:
        return 1.0
    z2 = z * z
    center = p + z2 / (2 * n)
    margin = z * sqrt(p * (1 - p) / n + z2 / (4 * n * n))
    return min(1.0, (center + margin) / (1 + z2 / n))


def _reweight_to_target_base_rate(risky: Sequence[bool], target: float) -> list[float]:
    """Per-row weights so the weighted base rate is ``target`` and weights sum to ``n``."""
    if not 0.0 < target < 1.0:
        raise ValueError("--approval-target-base-rate must be strictly between 0 and 1")
    n = len(risky)
    n_risky = sum(risky)
    n_benign = n - n_risky
    if n_risky == 0 or n_benign == 0:
        raise ValueError("cannot reweight to a target base rate: split contains only one class")
    w_risky = target * n / n_risky
    w_benign = (1.0 - target) * n / n_benign
    return [w_risky if r else w_benign for r in risky]


def _compute_curve(
    order: Sequence[int],
    risky: Sequence[bool],
    weights: Sequence[float],
    base_decisions: Sequence[Decision],
    budgets: Sequence[float],
    mode: IncidentRateMode,
    n: int,
) -> tuple[list[ApprovalCurvePoint], list[ApprovalOperatingPoint], float | None]:
    cum_w = 0.0
    cum_w2 = 0.0
    cum_risky_w = 0.0
    rate_at_rank: list[float | None] = [None] * (n + 1)
    curve: list[ApprovalCurvePoint] = []
    for rank, i in enumerate(order, start=1):
        w = weights[i]
        cum_w += w
        cum_w2 += w * w
        if risky[i]:
            cum_risky_w += w
        phat = cum_risky_w / cum_w
        if mode is IncidentRateMode.SMOOTHED:
            n_eff = (cum_w * cum_w) / cum_w2 if cum_w2 > 0 else 0.0
            rate = _wilson_upper_bound(phat, n_eff)
        else:
            rate = phat
        rate_at_rank[rank] = rate
        curve.append(ApprovalCurvePoint(allow_fraction=cum_w / n, incident_rate=rate))
    base_rate = cum_risky_w / cum_w if cum_w > 0 else None

    operating_points: list[ApprovalOperatingPoint] = []
    for budget in budgets:
        best_k = 0
        for k in range(1, n + 1):
            rate = rate_at_rank[k]
            if rate is not None and rate <= budget:
                best_k = k
        allowed = set(order[:best_k])
        allow_w = sum(weights[i] for i in allowed)
        deny_w = sum(
            weights[i] for i in range(n) if i not in allowed and base_decisions[i] is Decision.DENY
        )
        n_deny = sum(1 for i in range(n) if i not in allowed and base_decisions[i] is Decision.DENY)
        n_allow = best_k
        n_review = n - n_allow - n_deny
        review_w = n - allow_w - deny_w
        operating_points.append(
            ApprovalOperatingPoint(
                budget=budget,
                approvals_eliminated=allow_w / n,
                incident_rate=rate_at_rank[best_k] if best_k > 0 else None,
                review_fraction=review_w / n,
                deny_fraction=deny_w / n,
                n_allow=n_allow,
                n_review=n_review,
                n_deny=n_deny,
            )
        )
    return curve, operating_points, base_rate


def approval_elimination_curve(
    engine: DeterministicPolicyEngine,
    responses: Sequence[ClassifyResponse],
    examples: Sequence[Example],
    *,
    budgets: Sequence[float] = DEFAULT_BUDGETS,
    target_base_rate: float | None = None,
    incident_rate_mode: IncidentRateMode = IncidentRateMode.PREFIX,
) -> ApprovalElimination:
    """Approval-elimination curve for ``engine``'s bundle over ``responses``/``examples``.

    Ranks examples ascending by ``expected_costs(bundle, response).allow`` (cheapest,
    hence safest, to auto-allow first). Ground truth "risky" is any ``YES`` label on a
    dimension the bundle's rules reference (:func:`bundle_covered_dimensions`). For
    each ``budget`` in ``budgets``, finds the largest prefix of the ranked order (an
    auto-allow set) whose incident rate (see ``incident_rate_mode``) is ``<= budget``.
    Examples outside that allow-set keep the bundle's own ``DENY`` decision
    (``engine.evaluate``); everything else counts as ``REVIEW``, since converting a
    former allow/review into a *confident* auto-allow is exactly what this curve
    measures, while a bundle's own hard denies are unaffected by the budget sweep.

    ``incident_rate_mode=PREFIX`` (default) uses the point estimate, the realised
    fraction of the prefix that is risky; ``SMOOTHED`` instead uses a 95% Wilson upper
    bound on that estimate, which is more conservative but robust to a single
    low-scored risky row dominating a tiny prefix.

    ``target_base_rate``, if given, importance-reweights rows so the weighted base
    incident rate equals it (weights sum to ``n``), and all curve/operating-point
    fractions become weighted fractions, reported as ``reweighted_curve`` /
    ``reweighted_operating_points`` alongside the unweighted ``curve`` /
    ``operating_points``.
    """
    if len(responses) != len(examples):
        raise ValueError("responses and examples must be the same length")
    bundle = engine.bundle
    covered = bundle_covered_dimensions(bundle)
    n = len(examples)
    if n == 0:
        return _empty_result(bundle.bundle_id, covered, budgets, incident_rate_mode)

    scores = [expected_costs(bundle, response).allow for response in responses]
    risky = [_is_risky(example, covered) for example in examples]
    base_decisions = [
        engine.evaluate(response, example.context).decision
        for response, example in zip(responses, examples, strict=True)
    ]
    order = sorted(range(n), key=lambda i: scores[i])

    ones = [1.0] * n
    curve, operating_points, base_incident_rate = _compute_curve(
        order, risky, ones, base_decisions, budgets, incident_rate_mode, n
    )

    weights: list[float] | None = None
    reweighted_curve: list[ApprovalCurvePoint] | None = None
    reweighted_operating_points: list[ApprovalOperatingPoint] | None = None
    effective_base_rate: float | None = None
    if target_base_rate is not None:
        weights = _reweight_to_target_base_rate(risky, target_base_rate)
        reweighted_curve, reweighted_operating_points, effective_base_rate = _compute_curve(
            order, risky, weights, base_decisions, budgets, incident_rate_mode, n
        )

    return ApprovalElimination(
        bundle_id=bundle.bundle_id,
        covered_dimensions=sorted(covered),
        n=n,
        base_incident_rate=base_incident_rate,
        incident_rate_mode=incident_rate_mode,
        operating_points=operating_points,
        curve=curve,
        target_base_rate=target_base_rate,
        effective_base_rate=effective_base_rate,
        weights=weights,
        reweighted_operating_points=reweighted_operating_points,
        reweighted_curve=reweighted_curve,
    )
