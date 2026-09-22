"""Stratified, coverage-maximising sampler for ``forecheck judge sample``.

Two independent coverage goals are pursued at once by one greedy pass:

1. Every ``(dimension, label in {yes, no})`` cell should reach ``cell_target`` examples,
   capped at however many are actually available in the pool (``NOT_APPLICABLE`` and
   ``UNDETERMINED`` rows never count towards a cell -- they carry no yes/no signal).
2. Subject to (1), tool families and policy-predicate kinds should be as evenly
   represented as possible, so the judge-vs-generator comparison is not dominated by
   whichever family or kind happens to be most common in the pool.

The algorithm is a single greedy selection: at each step, score every remaining
candidate by how many still-under-target cells it would fill plus an inverse-frequency
bonus for its tool family and policy kinds, then take the best-scoring one. This is not
optimal (exact coverage maximisation is NP-hard in general) but it is deterministic,
cheap, and good enough for a few hundred stratified rows.
"""

from __future__ import annotations

import random
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, field

from forecheck.contracts import Example, LabelValue, RiskDimension
from forecheck.inference.serialization import render_context
from forecheck.judge.schema import JudgeSampleRow

__all__ = [
    "CELL_TARGET_DEFAULT",
    "SampleResult",
    "render_coverage_table",
    "stratified_sample",
]

CELL_TARGET_DEFAULT = 20

# Dominates the tool-family/policy-kind bonuses so cell coverage is always closed first.
_CELL_WEIGHT = 1000.0


def _tool_family_key(example: Example) -> str:
    family = example.tool_family or example.latent.tool.family
    return family.value if family is not None else "unknown"


def _policy_kinds(example: Example) -> tuple[str, ...]:
    return tuple(sorted({p.kind.value for p in example.latent.policy_predicates}))


def _cells(example: Example) -> frozenset[tuple[RiskDimension, LabelValue]]:
    return frozenset(
        (dimension, value)
        for dimension, value in example.labels.values.items()
        if value in (LabelValue.YES, LabelValue.NO)
    )


@dataclass(frozen=True, slots=True)
class _Candidate:
    example: Example
    cells: frozenset[tuple[RiskDimension, LabelValue]]
    tool_family: str
    policy_kinds: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SampleResult:
    rows: list[JudgeSampleRow]
    coverage: dict[str, object] = field(default_factory=dict)


def _cell_name(dimension: RiskDimension, value: LabelValue) -> str:
    return f"{dimension.value}:{value.value}"


def stratified_sample(
    examples: Sequence[Example],
    *,
    n: int,
    seed: int,
    cell_target: int = CELL_TARGET_DEFAULT,
) -> SampleResult:
    """Greedily select up to ``n`` examples maximising cell and family/kind coverage."""
    candidates = [
        _Candidate(
            example=e,
            cells=_cells(e),
            tool_family=_tool_family_key(e),
            policy_kinds=_policy_kinds(e),
        )
        for e in examples
    ]
    rng = random.Random(seed)  # noqa: S311 -- deterministic tie-breaking, not cryptographic
    order = list(range(len(candidates)))
    rng.shuffle(order)
    candidates = [candidates[i] for i in order]

    all_cells = [(d, v) for d in RiskDimension for v in (LabelValue.YES, LabelValue.NO)]
    cell_available: Counter[tuple[RiskDimension, LabelValue]] = Counter()
    for cand in candidates:
        for cell in cand.cells:
            cell_available[cell] += 1
    cell_target_effective = {cell: min(cell_target, cell_available[cell]) for cell in all_cells}

    cell_count: Counter[tuple[RiskDimension, LabelValue]] = Counter()
    tool_family_count: Counter[str] = Counter()
    policy_kind_count: Counter[str] = Counter()

    remaining = list(candidates)
    selected: list[_Candidate] = []
    n = min(n, len(remaining))

    while len(selected) < n and remaining:
        best_idx = -1
        best_score = -1.0
        for idx, cand in enumerate(remaining):
            score = 0.0
            for cell in cand.cells:
                if cell_count[cell] < cell_target_effective[cell]:
                    score += _CELL_WEIGHT
            score += 1.0 / (1 + tool_family_count[cand.tool_family])
            if cand.policy_kinds:
                score += sum(1.0 / (1 + policy_kind_count[k]) for k in cand.policy_kinds) / len(
                    cand.policy_kinds
                )
            if score > best_score:
                best_score = score
                best_idx = idx
        chosen = remaining.pop(best_idx)
        selected.append(chosen)
        for cell in chosen.cells:
            cell_count[cell] += 1
        tool_family_count[chosen.tool_family] += 1
        for kind in chosen.policy_kinds:
            policy_kind_count[kind] += 1

    rows = [
        JudgeSampleRow(
            example_id=cand.example.example_id,
            family_id=cand.example.family_id,
            split=cand.example.split,
            tool_family=cand.example.tool_family or cand.example.latent.tool.family,
            policy_kinds=cand.policy_kinds,
            difficulty=cand.example.difficulty,
            rendered_full=render_context(cand.example.context, strip_identity=False),
            rendered_stripped=render_context(cand.example.context, strip_identity=True),
            generator_labels=dict(cand.example.labels.values),
        )
        for cand in selected
    ]

    coverage = {
        "n_selected": len(selected),
        "n_pool": len(examples),
        "cell_target": cell_target,
        "cells": {
            _cell_name(dimension, value): {
                "selected": cell_count[(dimension, value)],
                "available": cell_available[(dimension, value)],
                "target": cell_target_effective[(dimension, value)],
            }
            for dimension, value in all_cells
        },
        "tool_families": dict(sorted(tool_family_count.items())),
        "policy_kinds": dict(sorted(policy_kind_count.items())),
    }
    return SampleResult(rows=rows, coverage=coverage)


def render_coverage_table(coverage: dict[str, object]) -> str:
    """Render ``coverage`` (as produced by :func:`stratified_sample`) as a text table."""
    lines: list[str] = []
    lines.append(f"selected {coverage['n_selected']} / pool {coverage['n_pool']}")
    lines.append("")
    lines.append(f"{'cell':<45}{'selected':>10}{'target':>10}{'available':>12}")
    cells = coverage["cells"]
    assert isinstance(cells, dict)
    for name, stats in cells.items():
        row = f"{stats['selected']:>10}{stats['target']:>10}{stats['available']:>12}"
        lines.append(f"{name:<45}{row}")
    lines.append("")
    tool_families = coverage["tool_families"]
    policy_kinds = coverage["policy_kinds"]
    assert isinstance(tool_families, dict)
    assert isinstance(policy_kinds, dict)
    families = ", ".join(f"{k}={v}" for k, v in tool_families.items())
    kinds = ", ".join(f"{k}={v}" for k, v in policy_kinds.items())
    lines.append(f"tool families: {families}")
    lines.append(f"policy kinds: {kinds}")
    return "\n".join(lines)
