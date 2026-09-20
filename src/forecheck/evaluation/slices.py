"""Slice definitions: named subsets of examples that per-dimension metrics are recomputed on.

A control that looks fine in aggregate and fails on one tool family, one difficulty
tier, or one contrastive axis is exactly the failure mode averaging hides. Every
built-in slice here returns plain index lists so :mod:`forecheck.evaluation.runner` can
recompute :mod:`forecheck.evaluation.metrics` on the restriction without this module
knowing anything about scores or predictions.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import Protocol

from forecheck.contracts import (
    ContextGap,
    ContrastiveAxis,
    DifficultyTier,
    Example,
    RiskDimension,
    Split,
    ToolFamily,
)
from forecheck.evaluation.metrics import DimensionMetrics, MetricName, macro_average

__all__ = [
    "Slice",
    "SliceLike",
    "context_gap_count_bucket",
    "rendered_context_length",
    "rendered_context_length_bucket",
    "slice_is_benign_hard_negative",
    "slice_policy_present_vs_absent",
    "slices_by_context_gap_count",
    "slices_by_difficulty",
    "slices_by_out_of_domain_tool",
    "slices_by_rendered_context_length_bucket",
    "slices_by_split",
    "slices_by_tool_family",
    "slices_by_trajectory_length_bucket",
    "surface_paraphrase_slices",
    "trajectory_length_bucket",
    "worst_slice",
]


@dataclass(frozen=True, slots=True)
class Slice:
    """A named predicate over :class:`~forecheck.contracts.Example`."""

    name: str
    predicate: Callable[[Example], bool]

    def select(self, examples: Sequence[Example]) -> list[int]:
        return [i for i, e in enumerate(examples) if self.predicate(e)]


def _tool_family_is(family: ToolFamily) -> Callable[[Example], bool]:
    def predicate(example: Example) -> bool:
        return example.tool_family is family

    return predicate


def slices_by_tool_family(examples: Sequence[Example]) -> list[Slice]:
    families = sorted({e.tool_family for e in examples if e.tool_family is not None}, key=str)
    return [Slice(f"tool_family={family.value}", _tool_family_is(family)) for family in families]


def _difficulty_is(tier: DifficultyTier) -> Callable[[Example], bool]:
    def predicate(example: Example) -> bool:
        return example.difficulty is tier

    return predicate


def slices_by_difficulty(examples: Sequence[Example]) -> list[Slice]:
    tiers = sorted({e.difficulty for e in examples}, key=str)
    return [Slice(f"difficulty={tier.value}", _difficulty_is(tier)) for tier in tiers]


def _split_is(split: Split) -> Callable[[Example], bool]:
    def predicate(example: Example) -> bool:
        return example.split is split

    return predicate


def slices_by_split(examples: Sequence[Example]) -> list[Slice]:
    splits = sorted({e.split for e in examples if e.split is not None}, key=str)
    return [Slice(f"split={split.value}", _split_is(split)) for split in splits]


def _contrastive_axis_is(axis: ContrastiveAxis) -> Callable[[Example], bool]:
    def predicate(example: Example) -> bool:
        return example.transformation is not None and example.transformation.axis is axis

    return predicate


def slices_by_contrastive_axis(examples: Sequence[Example]) -> list[Slice]:
    """One slice per :class:`ContrastiveAxis` present among *transformed* rows.

    Base rows of a pair (``transformation is None``) never match; this slice is only
    about the transformed half of each pair.
    """
    axes = sorted(
        {e.transformation.axis for e in examples if e.transformation is not None}, key=str
    )
    return [Slice(f"contrastive_axis={axis.value}", _contrastive_axis_is(axis)) for axis in axes]


def _is_surface_paraphrase(example: Example) -> bool:
    return (
        example.transformation is not None
        and example.transformation.axis is ContrastiveAxis.SURFACE_PARAPHRASE
    )


def surface_paraphrase_slices(examples: Sequence[Example]) -> list[Slice]:
    return [Slice("contrastive_axis=surface_paraphrase", _is_surface_paraphrase)]


def trajectory_length_bucket(length: int) -> str:
    if length == 0:
        return "0"
    if length <= 3:
        return "1-3"
    if length <= 10:
        return "4-10"
    return "11+"


def _trajectory_length_bucket_is(bucket: str) -> Callable[[Example], bool]:
    def predicate(example: Example) -> bool:
        return trajectory_length_bucket(len(example.context.trajectory)) == bucket

    return predicate


def slices_by_trajectory_length_bucket(examples: Sequence[Example]) -> list[Slice]:
    buckets = ["0", "1-3", "4-10", "11+"]
    return [
        Slice(f"trajectory_length={bucket}", _trajectory_length_bucket_is(bucket))
        for bucket in buckets
    ]


def _is_benign_hard_negative(example: Example) -> bool:
    return example.latent.is_benign_hard_negative


def slice_is_benign_hard_negative() -> Slice:
    return Slice("is_benign_hard_negative", _is_benign_hard_negative)


def context_gap_count_bucket(count: int) -> str:
    if count == 0:
        return "0"
    if count == 1:
        return "1"
    if count == 2:
        return "2"
    return "3+"


def _non_none_gap_count(example: Example) -> int:
    return sum(1 for gap in example.latent.context_gaps if gap is not ContextGap.NONE)


def _context_gap_count_bucket_is(bucket: str) -> Callable[[Example], bool]:
    def predicate(example: Example) -> bool:
        return context_gap_count_bucket(_non_none_gap_count(example)) == bucket

    return predicate


def slices_by_context_gap_count(examples: Sequence[Example]) -> list[Slice]:
    buckets = ["0", "1", "2", "3+"]
    return [
        Slice(f"context_gaps={bucket}", _context_gap_count_bucket_is(bucket)) for bucket in buckets
    ]


def rendered_context_length(example: Example) -> int:
    """Approximate character length of the textual context available to a backend.

    This module deliberately does not depend on :mod:`forecheck.generation` (owned by
    another workstream and not safe to import here), so this is a proxy computed purely
    from :class:`~forecheck.contracts.context.ActionContext` fields rather than the
    actual rendered prompt. It is intended only to bucket examples by "how much text",
    not to reproduce the exact prompt length.
    """
    context = example.context
    total = len(context.objective.text)
    total += len(context.proposed_action.tool_name)
    total += len(context.proposed_action.tool_description or "")
    total += len(str(context.proposed_action.arguments))
    total += sum(len(o.content) for o in context.observations)
    total += sum(len(s.result_summary or "") for s in context.trajectory)
    total += sum(len(p.text) for p in context.policies)
    return total


def rendered_context_length_bucket(length: int) -> str:
    if length < 1_000:
        return "<1k"
    if length < 4_000:
        return "1k-4k"
    if length < 16_000:
        return "4k-16k"
    return "16k+"


def _context_length_bucket_is(bucket: str) -> Callable[[Example], bool]:
    def predicate(example: Example) -> bool:
        return rendered_context_length_bucket(rendered_context_length(example)) == bucket

    return predicate


def slices_by_rendered_context_length_bucket(examples: Sequence[Example]) -> list[Slice]:
    buckets = ["<1k", "1k-4k", "4k-16k", "16k+"]
    return [
        Slice(f"context_length={bucket}", _context_length_bucket_is(bucket)) for bucket in buckets
    ]


def _policy_present(example: Example) -> bool:
    return len(example.context.policies) > 0


def _policy_absent(example: Example) -> bool:
    return len(example.context.policies) == 0


def slice_policy_present_vs_absent() -> list[Slice]:
    return [
        Slice("policy_present", _policy_present),
        Slice("policy_absent", _policy_absent),
    ]


def _out_of_domain_tool(training_tool_names: frozenset[str]) -> Callable[[Example], bool]:
    def predicate(example: Example) -> bool:
        return example.context.proposed_action.tool_name not in training_tool_names

    return predicate


def slices_by_out_of_domain_tool(training_tool_names: frozenset[str]) -> Slice:
    """Rows whose proposed tool name was never seen in ``training_tool_names``."""
    return Slice("out_of_domain_tool", _out_of_domain_tool(training_tool_names))


class SliceLike(Protocol):
    """Structural type satisfied by ``report.SliceReport`` without importing it.

    Declared with read-only ``@property`` members (rather than plain attribute
    annotations) so that frozen pydantic models — whose fields are read-only — satisfy
    this protocol structurally.
    """

    @property
    def name(self) -> str: ...

    @property
    def dimensions(self) -> Mapping[RiskDimension, DimensionMetrics]: ...


class _HasSlices(Protocol):
    @property
    def slices(self) -> Sequence[SliceLike]: ...


def worst_slice(report: _HasSlices, metric: MetricName) -> tuple[str, float] | None:
    """The (slice name, value) with the lowest macro value of ``metric``, or ``None``."""
    best: tuple[str, float] | None = None
    for sl in report.slices:
        value = macro_average(sl.dimensions, metric)
        if value is None:
            continue
        if best is None or value < best[1]:
            best = (sl.name, value)
    return best
