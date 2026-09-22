"""Shared fixtures for the LLM-judge test suite, built on top of
:mod:`tests.evaluation.conftest`'s ``make_example`` so example construction stays in one
place across suites.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from forecheck.contracts import Example, LabelValue, PolicyPredicateKind, RiskDimension, ToolFamily
from forecheck.contracts.latent import PolicyPredicate
from tests.evaluation.conftest import make_example

__all__ = ["make_judge_example"]


def make_judge_example(
    example_id: str = "ex-1",
    family_id: str | None = None,
    *,
    labels: Mapping[RiskDimension, LabelValue] | None = None,
    tool_family: ToolFamily = ToolFamily.EMAIL_MESSAGING,
    policy_kinds: Sequence[PolicyPredicateKind] = (),
) -> Example:
    """Build an :class:`Example` with the given labels, tool family and policy-predicate
    kinds, for sampler/agreement tests that need to control stratification inputs."""
    example = make_example(
        example_id=example_id,
        family_id=family_id or f"{example_id}-fam",
        labels=labels,
        tool_family=tool_family,
    )
    predicates = [
        PolicyPredicate(id=f"{example_id}-pred-{i}", kind=kind)
        for i, kind in enumerate(policy_kinds)
    ]
    new_latent = example.latent.model_copy(update={"policy_predicates": predicates})
    return example.model_copy(update={"latent": new_latent})
