"""Pydantic schema for the forecheck policy DSL.

A policy bundle is declarative YAML: a list of rules, each guarding a decision behind a
condition tree built from ``all`` / ``any`` / ``not`` combinators over ``score`` and
``fact`` leaf predicates. There is no embedded code path and nothing here calls
``eval``; every node is a typed, validated Pydantic model, so a malformed bundle fails
to parse rather than silently misbehaving at evaluation time.

This module only defines and structurally validates the schema. Cross-referencing
``fact`` names against the engine's registered fact table is deliberately left to
:mod:`forecheck.policies.loader`, which is the layer allowed to know about the engine.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forecheck.contracts import (
    META_DIMENSIONS,
    Decision,
    DecisionMode,
    ObligationKind,
    RiskDimension,
    RuleKind,
)

__all__ = [
    "CRITICAL_COST_DIMENSIONS",
    "HIGH_COST_DIMENSIONS",
    "Condition",
    "Cost",
    "DecisionMode",
    "FactValue",
    "PolicyBundle",
    "Rule",
    "UnknownAs",
    "default_cost_for_dimension",
]

FactValue = bool | int | float | str


class UnknownAs(StrEnum):
    """How an unknown quantity is treated while evaluating a condition tree.

    An unknown quantity is either an abstained :class:`RiskDimension` score or a
    context fact that could not be derived (including the case where no
    :class:`~forecheck.contracts.ActionContext` was supplied at all).

    * ``WORST_CASE`` (the safe default): a restrictive rule (``review``/``deny``)
      resolves an unknown condition as matching; an ``allow``-decision rule resolves it
      as not matching. Uncertainty is never allowed to make the outcome less safe.
    * ``ZERO``: an unknown condition never matches, as if every unknown quantity were
      the identity value for a ``gte``/``gt`` threshold check (probability or count of
      zero, fact absent). This is the legacy "abstention means safe" behaviour and is
      never the default.
    * ``ABSTAIN``: an unknown condition never matches, and no bias is applied based on
      the rule's decision. Equivalent to ``ZERO`` in this engine's resolution, kept as a
      distinct, explicit vocabulary word for bundle authors who want to say "I decline
      to guess" rather than "I assume the safe value is zero".
    """

    WORST_CASE = "worst_case"
    ZERO = "zero"
    ABSTAIN = "abstain"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class Cost(_Model):
    """Cost block for ``decision_mode: expected_cost``.

    ``allow_if_risky`` is paid when ``ALLOW`` is chosen and the dimension is truly
    risky; ``deny_if_benign`` is paid when ``DENY`` is chosen and the dimension is
    truly benign; ``review`` is paid whenever ``REVIEW`` is chosen, regardless of
    truth. See :func:`default_cost_for_dimension` for the severity-derived defaults
    and ``docs/policy-dsl.md`` for the objective these feed.
    """

    allow_if_risky: float = Field(gt=0.0)
    review: float = Field(ge=0.0)
    deny_if_benign: float = Field(gt=0.0)


CRITICAL_COST_DIMENSIONS: frozenset[RiskDimension] = frozenset(
    {
        RiskDimension.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION,
        RiskDimension.SENSITIVE_DATA_EXPOSURE,
        RiskDimension.UNTRUSTED_DESTINATION,
    }
)
"""Irreversible-or-exfiltration dimensions: the highest default cost tier."""

HIGH_COST_DIMENSIONS: frozenset[RiskDimension] = frozenset(
    {
        RiskDimension.PRIVILEGE_ESCALATION,
        RiskDimension.FINANCIAL_COMMITMENT,
        RiskDimension.UNAUTHORIZED_SCOPE,
    }
)
"""High-severity dimensions that are neither irreversible nor exfiltration."""

_COST_BY_TIER: dict[str, Cost] = {
    "critical": Cost(allow_if_risky=10.0, review=0.5, deny_if_benign=2.0),
    "high": Cost(allow_if_risky=5.0, review=0.3, deny_if_benign=1.5),
    "standard": Cost(allow_if_risky=3.0, review=0.2, deny_if_benign=1.0),
    "meta": Cost(allow_if_risky=1.0, review=0.1, deny_if_benign=1.0),
}


def default_cost_for_dimension(dimension: RiskDimension) -> Cost:
    """Severity-derived default :class:`Cost` for a dimension with no explicit block.

    | Tier | Membership | allow_if_risky | review | deny_if_benign |
    |---|---|---|---|---|
    | critical | :data:`CRITICAL_COST_DIMENSIONS` | 10.0 | 0.5 | 2.0 |
    | high | :data:`HIGH_COST_DIMENSIONS` | 5.0 | 0.3 | 1.5 |
    | meta | :data:`~forecheck.contracts.META_DIMENSIONS` | 1.0 | 0.1 | 1.0 |
    | standard | everything else | 3.0 | 0.2 | 1.0 |

    Full worked table and rationale: ``docs/policy-dsl.md``.
    """
    if dimension in CRITICAL_COST_DIMENSIONS:
        return _COST_BY_TIER["critical"]
    if dimension in HIGH_COST_DIMENSIONS:
        return _COST_BY_TIER["high"]
    if dimension in META_DIMENSIONS:
        return _COST_BY_TIER["meta"]
    return _COST_BY_TIER["standard"]


class Condition(_Model):
    """One node of a rule's condition tree.

    Exactly one of ``all``, ``any``, ``not``, ``score`` or ``fact`` must be set. The
    first three are combinators over child :class:`Condition` nodes; ``score`` and
    ``fact`` are leaf predicates.
    """

    all_: list[Condition] | None = Field(default=None, alias="all")
    any_: list[Condition] | None = Field(default=None, alias="any")
    not_: Condition | None = Field(default=None, alias="not")

    score: RiskDimension | None = None
    fact: str | None = None

    gte: float | None = None
    gt: float | None = None
    lte: float | None = None
    lt: float | None = None
    is_: FactValue | None = Field(default=None, alias="is")
    in_: list[FactValue] | None = Field(default=None, alias="in")

    @model_validator(mode="after")
    def _exactly_one_node_kind(self) -> Condition:
        kinds = {
            "all": self.all_ is not None,
            "any": self.any_ is not None,
            "not": self.not_ is not None,
            "score": self.score is not None,
            "fact": self.fact is not None,
        }
        present = [name for name, is_set in kinds.items() if is_set]
        if len(present) != 1:
            raise ValueError(
                "a condition node must set exactly one of all/any/not/score/fact, "
                f"got: {present or 'none'}"
            )
        if self.all_ is not None and not self.all_:
            raise ValueError("'all' must list at least one child condition")
        if self.any_ is not None and not self.any_:
            raise ValueError("'any' must list at least one child condition")
        if self.score is not None and all(
            t is None for t in (self.gte, self.gt, self.lte, self.lt)
        ):
            raise ValueError(
                f"score condition on {self.score!r} requires at least one of gte/gt/lte/lt"
            )
        if self.fact is not None and all(
            v is None for v in (self.is_, self.in_, self.gte, self.lte)
        ):
            raise ValueError(f"fact condition on {self.fact!r} requires one of is/in/gte/lte")
        return self


Condition.model_rebuild()


class Rule(_Model):
    """One named branch of policy: a condition, the decision it drives, and its
    obligations."""

    id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    decision: Decision
    when: Condition
    hard: bool = False
    kind: RuleKind = RuleKind.STANDARD
    obligations: list[ObligationKind] = Field(default_factory=list)
    cost: Cost | None = Field(
        default=None,
        description="Only consulted under decision_mode: expected_cost. Overrides "
        "default_cost_for_dimension() for whichever RiskDimension(s) this rule's "
        "'when' tree references.",
    )

    @model_validator(mode="after")
    def _allow_override_constraints(self) -> Rule:
        if self.kind is RuleKind.ALLOW_OVERRIDE:
            if self.decision is not Decision.ALLOW:
                raise ValueError(f"rule {self.id!r}: kind=allow_override requires decision: allow")
            if not self.obligations:
                raise ValueError(
                    f"rule {self.id!r}: kind=allow_override requires at least one "
                    "obligation, so an override is always auditable"
                )
            if self.hard:
                raise ValueError(
                    f"rule {self.id!r}: a rule cannot be both hard and allow_override; "
                    "hard is what an allow_override rule is unable to beat"
                )
        return self


class PolicyBundle(_Model):
    """A complete, versioned set of policy rules plus the fallbacks that apply when no
    rule fires or the classification is uncalibrated."""

    bundle_id: str = Field(min_length=1)
    version: Annotated[int, Field(ge=1)]
    dsl_version: str = Field(min_length=1)
    description: str = Field(min_length=1)
    default_decision: Decision
    uncalibrated_decision: Decision = Decision.REVIEW
    allow_uncalibrated: bool = False
    unknown_as: UnknownAs = UnknownAs.WORST_CASE
    decision_mode: DecisionMode = DecisionMode.THRESHOLD
    rules: list[Rule] = Field(default_factory=list)

    @model_validator(mode="after")
    def _unique_rule_ids(self) -> PolicyBundle:
        ids = [rule.id for rule in self.rules]
        duplicates = {rule_id for rule_id in ids if ids.count(rule_id) > 1}
        if duplicates:
            raise ValueError(f"duplicate rule ids in bundle {self.bundle_id!r}: {duplicates}")
        return self
