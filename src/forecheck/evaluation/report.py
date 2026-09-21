"""The evaluation report: what a run produced, and how to write it out.

``EvaluationReport.evaluation_class`` has no default. Every report must say, in the
type system, whether its numbers come from in-distribution synthetic data, adversarial
synthetic data, or external/human-reviewed data — because those three claims are not
interchangeable, and the markdown writer refuses to print a headline number without
naming which one applies.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from forecheck.contracts import CalibrationInfo, ModelInfo, RiskDimension, Split
from forecheck.evaluation.consistency import (
    CounterfactualSensitivityResult,
    InvarianceResult,
    PairConsistencyResult,
)
from forecheck.evaluation.decisions import DecisionMetricsResult
from forecheck.evaluation.latency import LatencyReport
from forecheck.evaluation.metrics import DimensionMetrics
from forecheck.evaluation.selective import SelectiveResult

__all__ = [
    "SYNTHETIC_CLASSES",
    "ConsistencyReport",
    "DatasetIdentity",
    "EvaluationClass",
    "EvaluationReport",
    "SliceReport",
]

_SYNTHETIC_DISCLAIMER = "Synthetic data. No real-world safety claim is made."

THRESHOLD_SELECTION_CRITERION = (
    "F1-optimal threshold (argmax F1 over the precision-recall curve), "
    "selected on a split disjoint from the one being reported"
)


class EvaluationClass(StrEnum):
    SYNTHETIC_IN_DISTRIBUTION = "synthetic_in_distribution"
    SYNTHETIC_HELDOUT_ADVERSARIAL = "synthetic_heldout_adversarial"
    EXTERNAL_OR_HUMAN = "external_or_human"


SYNTHETIC_CLASSES: frozenset[EvaluationClass] = frozenset(
    {EvaluationClass.SYNTHETIC_IN_DISTRIBUTION, EvaluationClass.SYNTHETIC_HELDOUT_ADVERSARIAL}
)


class DatasetIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    split: Split | None
    n: int
    sha256: str | None = None


class SliceReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    n: int
    dimensions: dict[RiskDimension, DimensionMetrics]


class ConsistencyReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    pair_consistency: PairConsistencyResult
    counterfactual_sensitivity: CounterfactualSensitivityResult
    invariance: InvarianceResult


class EvaluationReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    evaluation_class: EvaluationClass
    dataset: DatasetIdentity
    model: ModelInfo | None = None
    calibration: CalibrationInfo | None = None
    seed: int
    created_at: datetime
    identity_stripped: bool = False
    threshold_selection_split: Split | None = None
    dimensions: dict[RiskDimension, DimensionMetrics]
    macro: dict[str, float | None]
    worst_slice: dict[str, tuple[str, float] | None]
    slices: list[SliceReport] = Field(default_factory=list)
    consistency: ConsistencyReport | None = None
    selective: dict[RiskDimension, SelectiveResult] | None = None
    decisions: DecisionMetricsResult | None = None
    latency: LatencyReport | None = None

    def to_json(self, path: Path) -> None:
        path.write_text(self.model_dump_json(indent=2))

    def to_markdown(self, path: Path) -> None:
        path.write_text(self._render_markdown())

    def _render_markdown(self) -> str:
        lines: list[str] = []
        lines.append(f"# forecheck evaluation report — {self.evaluation_class.value.upper()}")
        lines.append("")
        if self.evaluation_class in SYNTHETIC_CLASSES:
            lines.append(f"> **{_SYNTHETIC_DISCLAIMER}**")
            lines.append("")
        lines.append(
            f"Dataset: split={self.dataset.split}, n={self.dataset.n}, "
            f"sha256={self.dataset.sha256 or 'n/a'}"
        )
        lines.append(f"Seed: {self.seed}. Generated at: {self.created_at.isoformat()}.")
        if self.model is not None:
            lines.append(f"Model: {self.model.backend}/{self.model.model_id}")
        lines.append(f"Identity stripped: {str(self.identity_stripped).lower()}")
        selection_split = (
            self.threshold_selection_split.value if self.threshold_selection_split else "n/a"
        )
        lines.append(
            f"Threshold selection: {THRESHOLD_SELECTION_CRITERION}. "
            f"Selection split: {selection_split}. Reported split: {self.dataset.split}."
        )
        lines.append("")
        lines.append("## Per-dimension metrics")
        lines.append("")
        lines.append(
            "| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | "
            "precision@selected | recall@selected | f1@selected | auprc | auroc | ece |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|---|---|")
        for dimension, metric in self.dimensions.items():
            f1_at_threshold = metric.at_threshold.f1 if metric.at_threshold is not None else None
            optimal = metric.at_optimal_threshold
            lines.append(
                f"| {dimension.value} | {metric.n_evaluable} | "
                f"{_fmt(metric.positive_rate)} | {_fmt(f1_at_threshold)} | "
                f"{_fmt(metric.optimal_threshold)} | "
                f"{_fmt(optimal.precision if optimal is not None else None)} | "
                f"{_fmt(optimal.recall if optimal is not None else None)} | "
                f"{_fmt(optimal.f1 if optimal is not None else None)} | "
                f"{_fmt(metric.auprc)} | {_fmt(metric.auroc)} | {_fmt(metric.ece)} |"
            )
        lines.append("")
        lines.append("## Macro / worst slice")
        lines.append("")
        for name, value in self.macro.items():
            lines.append(f"- macro `{name}` = {_fmt(value)}")
        for name, entry in self.worst_slice.items():
            if entry is None:
                lines.append(f"- worst-slice `{name}` = n/a")
            else:
                slice_name, value = entry
                lines.append(f"- worst-slice `{name}` = {_fmt(value)} ({slice_name})")
        if self.consistency is not None:
            lines.append("")
            lines.append("## Consistency")
            pc = self.consistency.pair_consistency
            lines.append(
                f"- pair consistency: {_fmt(pc.fraction_correct_direction)} "
                f"over {pc.n_directional_pairs} directional pairs"
            )
            lines.append(
                "- counterfactual sensitivity (mean |dp|): "
                f"{_fmt(self.consistency.counterfactual_sensitivity.mean_abs_delta)}"
            )
            lines.append(
                "- surface-paraphrase invariance (mean |dp|): "
                f"{_fmt(self.consistency.invariance.mean_abs_delta)}, "
                f"fraction moved: {_fmt(self.consistency.invariance.fraction_any_dimension_moved)}"
            )
        if self.decisions is not None:
            lines.append("")
            lines.append("## Decisions")
            lines.append(f"- false allow rate: {_fmt(self.decisions.false_allow_rate)}")
            lines.append(f"- false deny rate: {_fmt(self.decisions.false_deny_rate)}")
            lines.append(f"- review rate: {_fmt(self.decisions.review_rate)}")
            lines.append(
                f"- mean risk-weighted cost: {_fmt(self.decisions.mean_risk_weighted_cost)}"
            )
        if self.latency is not None:
            lines.append("")
            lines.append("## Latency")
            overall = self.latency.overall
            lines.append(
                f"- p50={overall.p50_ms:.2f}ms p90={overall.p90_ms:.2f}ms "
                f"p99={overall.p99_ms:.2f}ms throughput={overall.throughput_items_per_s:.2f}/s"
            )
        return "\n".join(lines) + "\n"


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"
