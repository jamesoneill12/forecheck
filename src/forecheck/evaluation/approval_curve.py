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
    "approval_elimination_curve",
    "bundle_covered_dimensions",
]

DEFAULT_BUDGETS: tuple[float, ...] = (0.001, 0.005, 0.01, 0.02, 0.05)


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
    operating_points: list[ApprovalOperatingPoint]
    curve: list[ApprovalCurvePoint]

    def to_markdown(self) -> str:
        lines = ["## Approval elimination", ""]
        lines.append(
            f"Bundle `{self.bundle_id}`, n={self.n}, "
            f"base incident rate={_fmt(self.base_incident_rate)}. "
            "Ranking score: expected cost of ALLOW over the bundle's covered "
            f"dimensions ({', '.join(d.value for d in self.covered_dimensions)})."
        )
        lines.append("")
        lines.append("| budget | approvals eliminated | incident rate | review rate | deny rate |")
        lines.append("|---|---|---|---|---|")
        for point in self.operating_points:
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
    bundle_id: str, covered: frozenset[RiskDimension], budgets: Sequence[float]
) -> ApprovalElimination:
    return ApprovalElimination(
        bundle_id=bundle_id,
        covered_dimensions=sorted(covered),
        n=0,
        base_incident_rate=None,
        operating_points=[
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
        ],
        curve=[],
    )


def approval_elimination_curve(
    engine: DeterministicPolicyEngine,
    responses: Sequence[ClassifyResponse],
    examples: Sequence[Example],
    *,
    budgets: Sequence[float] = DEFAULT_BUDGETS,
) -> ApprovalElimination:
    """Approval-elimination curve for ``engine``'s bundle over ``responses``/``examples``.

    Ranks examples ascending by ``expected_costs(bundle, response).allow`` (cheapest,
    hence safest, to auto-allow first). Ground truth "risky" is any ``YES`` label on a
    dimension the bundle's rules reference (:func:`bundle_covered_dimensions`). For
    each ``budget`` in ``budgets``, finds the largest prefix of the ranked order (an
    auto-allow set) whose realised incident rate — the fraction of allowed examples
    that are risky — is ``<= budget``. Examples outside that allow-set keep the
    bundle's own ``DENY`` decision (``engine.evaluate``); everything else counts as
    ``REVIEW``, since converting a former allow/review into a *confident* auto-allow is
    exactly what this curve measures, while a bundle's own hard denies are unaffected
    by the budget sweep.
    """
    if len(responses) != len(examples):
        raise ValueError("responses and examples must be the same length")
    bundle = engine.bundle
    covered = bundle_covered_dimensions(bundle)
    n = len(examples)
    if n == 0:
        return _empty_result(bundle.bundle_id, covered, budgets)

    scores = [expected_costs(bundle, response).allow for response in responses]
    risky = [_is_risky(example, covered) for example in examples]
    base_decisions = [
        engine.evaluate(response, example.context).decision
        for response, example in zip(responses, examples, strict=True)
    ]
    order = sorted(range(n), key=lambda i: scores[i])

    cum_risky = 0
    incident_rate_at_k: list[float | None] = [None] * (n + 1)
    curve: list[ApprovalCurvePoint] = []
    for rank, i in enumerate(order, start=1):
        if risky[i]:
            cum_risky += 1
        rate = cum_risky / rank
        incident_rate_at_k[rank] = rate
        curve.append(ApprovalCurvePoint(allow_fraction=rank / n, incident_rate=rate))
    base_incident_rate = incident_rate_at_k[n]

    operating_points: list[ApprovalOperatingPoint] = []
    for budget in budgets:
        best_k = 0
        for k in range(1, n + 1):
            rate = incident_rate_at_k[k]
            if rate is not None and rate <= budget:
                best_k = k
        allowed = set(order[:best_k])
        n_deny = sum(1 for i in range(n) if i not in allowed and base_decisions[i] is Decision.DENY)
        n_allow = best_k
        n_review = n - n_allow - n_deny
        operating_points.append(
            ApprovalOperatingPoint(
                budget=budget,
                approvals_eliminated=n_allow / n,
                incident_rate=incident_rate_at_k[best_k] if best_k > 0 else None,
                review_fraction=n_review / n,
                deny_fraction=n_deny / n,
                n_allow=n_allow,
                n_review=n_review,
                n_deny=n_deny,
            )
        )

    return ApprovalElimination(
        bundle_id=bundle.bundle_id,
        covered_dimensions=sorted(covered),
        n=n,
        base_incident_rate=base_incident_rate,
        operating_points=operating_points,
        curve=curve,
    )
