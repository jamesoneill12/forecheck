"""Per-dimension classification, calibration and cost metrics.

**Label handling (non-negotiable).** ``LabelValue.NOT_APPLICABLE`` and
``LabelValue.UNDETERMINED`` cells are excluded from every per-dimension metric in this
module. They are never counted as negatives: a dimension that is all-``NOT_APPLICABLE``
(e.g. ``untrusted_destination`` on a scenario with no destination) has no ground truth
to score against, and silently treating it as "no risk" would inflate precision on rare
positives. Such a dimension yields ``n_evaluable=0`` and every scalar metric is
``None``, never a fabricated perfect score. A prediction with no probability (the
backend abstained on that dimension) is excluded the same way, for the same reason.

All metrics are computed on plain numpy arrays produced by
:func:`extract_dimension_arrays`, so this module has no dependency on any concrete
backend, calibrator or policy engine — only on :mod:`forecheck.contracts`.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

import numpy as np
from pydantic import BaseModel, ConfigDict
from sklearn.metrics import average_precision_score, precision_recall_curve, roc_auc_score

from forecheck.contracts import LabelValue, RiskDimension
from forecheck.evaluation.bootstrap import BootstrapResult

if TYPE_CHECKING:
    from numpy.typing import NDArray

__all__ = [
    "DimensionMetrics",
    "MetricName",
    "ReliabilityBin",
    "ThresholdMetrics",
    "attach_ci",
    "compute_dimension_metrics",
    "expected_calibration_error",
    "extract_dimension_arrays",
    "find_f1_optimal_threshold",
    "get_metric",
    "macro_average",
    "threshold_metrics",
]

EVALUABLE_LABELS: frozenset[LabelValue] = frozenset({LabelValue.YES, LabelValue.NO})

MetricName = str


class ThresholdMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    threshold: float
    precision: float
    recall: float
    f1: float


class ReliabilityBin(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    bin_center: float
    mean_predicted: float
    empirical_frequency: float
    count: int


class DimensionMetrics(BaseModel):
    """All metrics for one :class:`~forecheck.contracts.RiskDimension`.

    ``n_evaluable`` is the number of rows with a ``YES``/``NO`` label AND a
    non-abstained probability for this dimension. Every other field is ``None`` (or an
    empty tuple) when ``n_evaluable == 0``.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    dimension: RiskDimension
    n_evaluable: int
    n_positive: int
    positive_rate: float | None
    auprc: float | None
    auroc: float | None
    brier: float | None
    nll: float | None
    ece: float | None
    adaptive_ece: float | None
    reliability_bins: tuple[ReliabilityBin, ...]
    at_threshold: ThresholdMetrics | None
    at_optimal_threshold: ThresholdMetrics | None
    optimal_threshold: float | None
    ci: dict[str, BootstrapResult] | None = None


def extract_dimension_arrays(
    labels: Sequence[LabelValue],
    probabilities: Sequence[float | None],
) -> tuple[NDArray[np.int_], NDArray[np.float64], NDArray[np.intp]]:
    """Build parallel ``(y_true, y_prob, kept_indices)`` arrays for one dimension.

    Rows whose label is ``NOT_APPLICABLE``/``UNDETERMINED``, or whose probability is
    ``None`` (the backend abstained), are dropped from all three arrays together.
    ``kept_indices`` are positions into the original ``labels``/``probabilities``
    sequences, so callers can align other per-row data (e.g. family id, for stratified
    bootstrapping) with the filtered arrays.
    """
    y_true: list[int] = []
    y_prob: list[float] = []
    kept: list[int] = []
    for i, (label, prob) in enumerate(zip(labels, probabilities, strict=True)):
        if label not in EVALUABLE_LABELS or prob is None:
            continue
        y_true.append(1 if label is LabelValue.YES else 0)
        y_prob.append(prob)
        kept.append(i)
    return (
        np.array(y_true, dtype=np.int_),
        np.array(y_prob, dtype=np.float64),
        np.array(kept, dtype=np.intp),
    )


def threshold_metrics(
    y_true: NDArray[np.int_], y_prob: NDArray[np.float64], threshold: float
) -> ThresholdMetrics:
    y_pred = (y_prob >= threshold).astype(np.int_)
    tp = int(np.sum((y_pred == 1) & (y_true == 1)))
    fp = int(np.sum((y_pred == 1) & (y_true == 0)))
    fn = int(np.sum((y_pred == 0) & (y_true == 1)))
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    return ThresholdMetrics(threshold=threshold, precision=precision, recall=recall, f1=f1)


def find_f1_optimal_threshold(
    y_true: NDArray[np.int_], y_prob: NDArray[np.float64]
) -> tuple[float, ThresholdMetrics] | None:
    """Find the F1-optimal threshold on the given array.

    Callers must pass a *separate* selection array here, never the array a report's
    headline metrics are being computed on, or the "optimal" threshold is overfit to
    the number it is meant to explain.
    """
    if len(y_true) == 0 or len(np.unique(y_true)) < 2:
        return None
    precisions, recalls, thresholds = precision_recall_curve(y_true, y_prob)
    precisions, recalls = precisions[:-1], recalls[:-1]
    if len(thresholds) == 0:
        return None
    denom = precisions + recalls
    f1s = np.divide(2 * precisions * recalls, denom, out=np.zeros_like(denom), where=denom > 0)
    best_idx = int(np.argmax(f1s))
    best_threshold = float(thresholds[best_idx])
    return best_threshold, ThresholdMetrics(
        threshold=best_threshold,
        precision=float(precisions[best_idx]),
        recall=float(recalls[best_idx]),
        f1=float(f1s[best_idx]),
    )


def _equal_width_bins(
    y_true: NDArray[np.int_], y_prob: NDArray[np.float64], n_bins: int
) -> list[ReliabilityBin]:
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    bins: list[ReliabilityBin] = []
    for i in range(n_bins):
        lo, hi = edges[i], edges[i + 1]
        mask = (y_prob >= lo) & (y_prob < hi) if i < n_bins - 1 else (y_prob >= lo) & (y_prob <= hi)
        count = int(np.sum(mask))
        if count == 0:
            continue
        bins.append(
            ReliabilityBin(
                bin_center=float((lo + hi) / 2),
                mean_predicted=float(np.mean(y_prob[mask])),
                empirical_frequency=float(np.mean(y_true[mask])),
                count=count,
            )
        )
    return bins


def _equal_mass_bins(
    y_true: NDArray[np.int_], y_prob: NDArray[np.float64], n_bins: int
) -> list[ReliabilityBin]:
    n = len(y_true)
    if n == 0:
        return []
    order = np.argsort(y_prob)
    y_true_sorted = y_true[order]
    y_prob_sorted = y_prob[order]
    bins: list[ReliabilityBin] = []
    for idx in np.array_split(np.arange(n), min(n_bins, n)):
        if len(idx) == 0:
            continue
        probs = y_prob_sorted[idx]
        labels = y_true_sorted[idx]
        bins.append(
            ReliabilityBin(
                bin_center=float(np.mean(probs)),
                mean_predicted=float(np.mean(probs)),
                empirical_frequency=float(np.mean(labels)),
                count=len(idx),
            )
        )
    return bins


def expected_calibration_error(bins: Sequence[ReliabilityBin], n: int) -> float | None:
    if n == 0 or not bins:
        return None
    return float(sum(b.count / n * abs(b.mean_predicted - b.empirical_frequency) for b in bins))


def compute_dimension_metrics(
    dimension: RiskDimension,
    y_true: NDArray[np.int_],
    y_prob: NDArray[np.float64],
    *,
    threshold: float = 0.5,
    threshold_selection_true: NDArray[np.int_] | None = None,
    threshold_selection_prob: NDArray[np.float64] | None = None,
    n_bins: int = 10,
) -> DimensionMetrics:
    """Compute every metric for one dimension.

    ``threshold_selection_true``/``threshold_selection_prob`` are an optional
    *disjoint* array used only to locate the F1-optimal threshold; that threshold is
    then applied to ``y_true``/``y_prob`` to produce ``at_optimal_threshold``.
    """
    n = len(y_true)
    if n == 0:
        return DimensionMetrics(
            dimension=dimension,
            n_evaluable=0,
            n_positive=0,
            positive_rate=None,
            auprc=None,
            auroc=None,
            brier=None,
            nll=None,
            ece=None,
            adaptive_ece=None,
            reliability_bins=(),
            at_threshold=None,
            at_optimal_threshold=None,
            optimal_threshold=None,
        )
    n_positive = int(np.sum(y_true))
    positive_rate = n_positive / n
    n_classes = len(np.unique(y_true))
    auprc = float(average_precision_score(y_true, y_prob)) if n_classes > 1 else None
    auroc = float(roc_auc_score(y_true, y_prob)) if n_classes > 1 else None
    brier = float(np.mean((y_prob - y_true) ** 2))
    eps = 1e-12
    clipped = np.clip(y_prob, eps, 1 - eps)
    nll = float(-np.mean(y_true * np.log(clipped) + (1 - y_true) * np.log(1 - clipped)))
    width_bins = _equal_width_bins(y_true, y_prob, n_bins)
    mass_bins = _equal_mass_bins(y_true, y_prob, n_bins)
    ece = expected_calibration_error(width_bins, n)
    adaptive_ece = expected_calibration_error(mass_bins, n)
    at_threshold = threshold_metrics(y_true, y_prob, threshold)
    optimal_threshold: float | None = None
    at_optimal: ThresholdMetrics | None = None
    if threshold_selection_true is not None and threshold_selection_prob is not None:
        found = find_f1_optimal_threshold(threshold_selection_true, threshold_selection_prob)
        if found is not None:
            optimal_threshold, _ = found
            at_optimal = threshold_metrics(y_true, y_prob, optimal_threshold)
    return DimensionMetrics(
        dimension=dimension,
        n_evaluable=n,
        n_positive=n_positive,
        positive_rate=positive_rate,
        auprc=auprc,
        auroc=auroc,
        brier=brier,
        nll=nll,
        ece=ece,
        adaptive_ece=adaptive_ece,
        reliability_bins=tuple(width_bins),
        at_threshold=at_threshold,
        at_optimal_threshold=at_optimal,
        optimal_threshold=optimal_threshold,
    )


def get_metric(dm: DimensionMetrics, metric: MetricName) -> float | None:
    """Look up a scalar metric by name, for macro-averaging and slicing."""
    if metric == "precision":
        return dm.at_threshold.precision if dm.at_threshold is not None else None
    if metric == "recall":
        return dm.at_threshold.recall if dm.at_threshold is not None else None
    if metric == "f1":
        return dm.at_threshold.f1 if dm.at_threshold is not None else None
    if metric == "f1@selected":
        return dm.at_optimal_threshold.f1 if dm.at_optimal_threshold is not None else None
    if metric in {"auprc", "auroc", "brier", "nll", "ece", "adaptive_ece", "positive_rate"}:
        return getattr(dm, metric)  # type: ignore[no-any-return]
    raise KeyError(f"unknown metric name: {metric!r}")


def attach_ci(dm: DimensionMetrics, ci: dict[str, BootstrapResult]) -> DimensionMetrics:
    """Return a copy of ``dm`` with bootstrap CIs attached (``DimensionMetrics`` is frozen)."""
    return dm.model_copy(update={"ci": ci})


def macro_average(
    dimensions: Mapping[RiskDimension, DimensionMetrics], metric: MetricName
) -> float | None:
    """Mean of ``metric`` over dimensions that have a value for it."""
    values = [v for v in (get_metric(dm, metric) for dm in dimensions.values()) if v is not None]
    if not values:
        return None
    return float(np.mean(values))
