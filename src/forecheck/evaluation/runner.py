"""Orchestrates one evaluation run: backend x examples -> :class:`EvaluationReport`.

This module depends only on the protocols in :mod:`forecheck.inference.base`,
:mod:`forecheck.calibration.base` and :mod:`forecheck.policies.base`, plus
:mod:`forecheck.contracts` and the rest of :mod:`forecheck.evaluation`. It never
imports a concrete backend, calibrator or policy engine implementation.

**Calibration is deliberately not performed here.** A raw score only becomes a
probability by passing through a fitted :class:`~forecheck.calibration.base.Calibrator`,
and this module has no way to construct one from a
:class:`~forecheck.calibration.base.CalibratorBundle` without depending on the concrete
calibration methods it registers (owned by :mod:`forecheck.calibration.methods`, a
separate workstream). Callers that have already built ``Calibrator`` instances pass
them in via ``calibrators``; ``calibrator_bundle`` is accepted purely so its provenance
is recorded in the report. Without either, raw backend scores are used as-is, which is
only correct for a backend whose raw scale is already a probability (e.g. the mock
backend) — this mirrors the project's own separation of scoring from calibration.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import numpy as np

from forecheck.contracts import (
    CalibrationInfo,
    CalibrationMethod,
    ClassifyResponse,
    DimensionScore,
    Example,
    ModelInfo,
    RiskDimension,
    TruncationInfo,
)
from forecheck.evaluation import consistency, selective, slices
from forecheck.evaluation import decisions as decisions_mod
from forecheck.evaluation import stacking as stacking_mod
from forecheck.evaluation.approval_curve import (
    ApprovalElimination,
    IncidentRateMode,
    approval_elimination_curve,
)
from forecheck.evaluation.bootstrap import BootstrapResult, bootstrap_ci
from forecheck.evaluation.latency import LatencyReport, measure_latency
from forecheck.evaluation.metrics import (
    DimensionMetrics,
    attach_ci,
    compute_dimension_metrics,
    extract_dimension_arrays,
    get_metric,
    macro_average,
)
from forecheck.evaluation.report import (
    ConsistencyReport,
    DatasetIdentity,
    EvaluationClass,
    EvaluationReport,
    SliceReport,
)
from forecheck.evaluation.selective import SelectiveResult

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from forecheck.calibration.base import Calibrator, CalibratorBundle
    from forecheck.inference.base import ClassifierBackend, RawScores
    from forecheck.policies.base import PolicyEngine
    from forecheck.policies.dsl import PolicyBundle
    from forecheck.policies.engine import DeterministicPolicyEngine

    ThresholdSelectionArrays = dict[RiskDimension, tuple[NDArray[np.int_], NDArray[np.float64]]]

__all__ = ["evaluate"]

DEFAULT_CI_METRICS: tuple[str, ...] = ("f1", "auprc")
DEFAULT_MACRO_METRICS: tuple[str, ...] = (
    "precision",
    "recall",
    "f1",
    "f1@selected",
    "auprc",
    "auroc",
    "brier",
    "ece",
)

logger = logging.getLogger(__name__)


class _ReportView:
    """Minimal object satisfying :class:`forecheck.evaluation.slices._HasSlices`."""

    def __init__(self, slice_reports: Sequence[slices.SliceLike]) -> None:
        self.slices: Sequence[slices.SliceLike] = slice_reports


def _default_slices(
    examples: Sequence[Example], training_tool_names: frozenset[str] | None
) -> list[slices.Slice]:
    built: list[slices.Slice] = []
    built.extend(slices.slices_by_tool_family(examples))
    built.extend(slices.slices_by_difficulty(examples))
    built.extend(slices.slices_by_contrastive_axis(examples))
    built.extend(slices.surface_paraphrase_slices(examples))
    built.extend(slices.slices_by_trajectory_length_bucket(examples))
    built.extend(slices.slices_by_split(examples))
    built.append(slices.slice_is_benign_hard_negative())
    built.extend(slices.slices_by_context_gap_count(examples))
    built.extend(slices.slices_by_rendered_context_length_bucket(examples))
    built.extend(slices.slice_policy_present_vs_absent())
    if training_tool_names is not None:
        built.append(slices.slices_by_out_of_domain_tool(training_tool_names))
    return built


def _score_examples(
    backend: ClassifierBackend,
    examples: Sequence[Example],
    dimensions: Sequence[RiskDimension],
) -> list[RawScores]:
    return backend.score_batch([e.context for e in examples], dimensions)


def _raw_values(raw: Sequence[RawScores], dimension: RiskDimension) -> list[float | None]:
    return [None if dimension in r.abstained_dimensions else r.scores.get(dimension) for r in raw]


def _apply_calibration(
    values: list[float | None],
    calibrator: Calibrator | None,
) -> list[float | None]:
    if calibrator is None:
        return values
    indices = [i for i, v in enumerate(values) if v is not None]
    if not indices:
        return values
    arr = np.array([values[i] for i in indices], dtype=np.float64)
    transformed = calibrator.transform(arr)
    result = list(values)
    for idx, value in zip(indices, transformed, strict=True):
        result[idx] = float(value)
    return result


def _probability_matrix(
    raw: Sequence[RawScores],
    dimensions: Sequence[RiskDimension],
    calibrators: Mapping[RiskDimension, Calibrator] | None,
) -> dict[RiskDimension, list[float | None]]:
    matrix: dict[RiskDimension, list[float | None]] = {}
    for dimension in dimensions:
        values = _raw_values(raw, dimension)
        calibrator = calibrators.get(dimension) if calibrators is not None else None
        matrix[dimension] = _apply_calibration(values, calibrator)
    return matrix


def _dimension_metrics_for_indices(
    examples: Sequence[Example],
    probabilities: Mapping[RiskDimension, list[float | None]],
    dimensions: Sequence[RiskDimension],
    indices: Sequence[int],
    *,
    threshold: float,
    threshold_selection: ThresholdSelectionArrays | None,
) -> dict[RiskDimension, DimensionMetrics]:
    result: dict[RiskDimension, DimensionMetrics] = {}
    for dimension in dimensions:
        labels = [examples[i].labels.values[dimension] for i in indices]
        probs = [probabilities[dimension][i] for i in indices]
        y_true, y_prob, _ = extract_dimension_arrays(labels, probs)
        sel_true = sel_prob = None
        if threshold_selection is not None and dimension in threshold_selection:
            sel_true, sel_prob = threshold_selection[dimension]
        result[dimension] = compute_dimension_metrics(
            dimension,
            y_true,
            y_prob,
            threshold=threshold,
            threshold_selection_true=sel_true,
            threshold_selection_prob=sel_prob,
        )
    return result


def _build_threshold_selection(
    backend: ClassifierBackend,
    threshold_selection_examples: Sequence[Example],
    dims: Sequence[RiskDimension],
    calibrators: Mapping[RiskDimension, Calibrator] | None,
    precomputed: Sequence[RawScores] | None = None,
    on_scored: Callable[[Sequence[RawScores]], None] | None = None,
) -> ThresholdSelectionArrays:
    if precomputed is not None and len(precomputed) == len(threshold_selection_examples):
        sel_raw = list(precomputed)
    else:
        sel_raw = _score_examples(backend, threshold_selection_examples, dims)
        if on_scored is not None:
            on_scored(sel_raw)
    sel_probabilities = _probability_matrix(sel_raw, dims, calibrators)
    threshold_selection: ThresholdSelectionArrays = {}
    for dimension in dims:
        labels = [e.labels.values[dimension] for e in threshold_selection_examples]
        probs = sel_probabilities[dimension]
        sel_true, sel_prob, _ = extract_dimension_arrays(labels, probs)
        threshold_selection[dimension] = (sel_true, sel_prob)
    return threshold_selection


def _attach_bootstrap_cis(
    examples: Sequence[Example],
    dimension_metrics: Mapping[RiskDimension, DimensionMetrics],
    probabilities: Mapping[RiskDimension, list[float | None]],
    *,
    threshold: float,
    seed: int,
    n_boot: int,
    ci_metrics: Sequence[str],
) -> dict[RiskDimension, DimensionMetrics]:
    family_ids = [e.family_id for e in examples]
    out: dict[RiskDimension, DimensionMetrics] = {}
    for dimension, dm in dimension_metrics.items():
        labels = [e.labels.values[dimension] for e in examples]
        probs = probabilities[dimension]
        y_true, y_prob, kept = extract_dimension_arrays(labels, probs)
        if len(kept) == 0 or not ci_metrics:
            out[dimension] = dm
            continue
        strata = [family_ids[i] for i in kept]
        ci: dict[str, BootstrapResult] = {}
        for metric_name in ci_metrics:
            ci[metric_name] = bootstrap_ci(
                _bootstrap_statistic(dimension, y_true, y_prob, threshold, metric_name),
                len(kept),
                seed,
                n_boot=n_boot,
                strata=strata,
            )
        out[dimension] = attach_ci(dm, ci)
    return out


def _bootstrap_statistic(
    dimension: RiskDimension,
    y_true: NDArray[np.int_],
    y_prob: NDArray[np.float64],
    threshold: float,
    metric_name: str,
) -> Callable[[NDArray[np.intp]], float | None]:
    def _statistic(idx: NDArray[np.intp]) -> float | None:
        sub = compute_dimension_metrics(dimension, y_true[idx], y_prob[idx], threshold=threshold)
        return get_metric(sub, metric_name)

    return _statistic


def _build_classify_responses(
    examples: Sequence[Example],
    raw: Sequence[RawScores],
    probabilities: Mapping[RiskDimension, list[float | None]],
    dimensions: Sequence[RiskDimension],
    model_info: ModelInfo,
    calibration_info: CalibrationInfo,
) -> list[ClassifyResponse]:
    responses: list[ClassifyResponse] = []
    for i, (example, raw_scores) in enumerate(zip(examples, raw, strict=True)):
        scores: list[DimensionScore] = []
        for dimension in dimensions:
            prob = probabilities[dimension][i]
            abstained = dimension in raw_scores.abstained_dimensions
            scores.append(
                DimensionScore(
                    dimension=dimension,
                    probability=prob if not abstained else None,
                    raw_score=None if abstained else raw_scores.scores.get(dimension),
                    calibrated=prob is not None and not abstained,
                    abstained=abstained,
                )
            )
        responses.append(
            ClassifyResponse(
                request_id=example.example_id,
                scores=scores,
                model=model_info,
                calibration=calibration_info,
                truncation=TruncationInfo(),
                abstained=len(raw_scores.abstained_dimensions) > 0,
                latency_ms=0.0,
            )
        )
    return responses


def _calibration_info(
    calibrator_bundle: CalibratorBundle | None, dims: Sequence[RiskDimension]
) -> CalibrationInfo:
    if calibrator_bundle is None:
        return CalibrationInfo(method=CalibrationMethod.NONE)
    method = CalibrationMethod.NONE
    if dims and dims[0] in calibrator_bundle.dimensions:
        method = calibrator_bundle.dimensions[dims[0]].method
    return CalibrationInfo(
        method=method,
        artifact_id=calibrator_bundle.artifact_id,
        fitted_at=calibrator_bundle.fitted_at,
        fitted_on_split=calibrator_bundle.split_name,
        dataset_hash=calibrator_bundle.dataset_sha256,
    )


def evaluate(
    backend: ClassifierBackend,
    examples: Sequence[Example],
    *,
    evaluation_class: EvaluationClass,
    calibrators: Mapping[RiskDimension, Calibrator] | None = None,
    calibrator_bundle: CalibratorBundle | None = None,
    engine: PolicyEngine | None = None,
    extra_slices: Sequence[slices.Slice] = (),
    seed: int = 0,
    n_boot: int = 200,
    ci_metrics: Sequence[str] = DEFAULT_CI_METRICS,
    macro_metrics: Sequence[str] = DEFAULT_MACRO_METRICS,
    threshold: float = 0.5,
    dimensions: Sequence[RiskDimension] | None = None,
    threshold_selection_examples: Sequence[Example] | None = None,
    include_latency: bool = False,
    training_tool_names: frozenset[str] | None = None,
    dataset_sha256: str | None = None,
    identity_stripped: bool = False,
    labels_source: str | None = None,
    threshold_selection_scores: Sequence[RawScores] | None = None,
    on_threshold_selection_scored: Callable[[Sequence[RawScores]], None] | None = None,
    stacking_bundles: Sequence[PolicyBundle] = (),
    stacking_synthetic: bool = False,
    approval_curve_engine: DeterministicPolicyEngine | None = None,
    approval_target_base_rate: float | None = None,
    approval_incident_rate_mode: IncidentRateMode = IncidentRateMode.PREFIX,
    on_scored: Callable[[Sequence[RawScores], Mapping[RiskDimension, list[float | None]]], None]
    | None = None,
) -> EvaluationReport:
    """Run a full evaluation of ``backend`` on ``examples`` and return a report.

    ``evaluation_class`` is required (see
    :class:`~forecheck.evaluation.report.EvaluationClass`) so every report states, in
    the type system, what kind of claim its numbers support.
    """
    dims = list(dimensions) if dimensions is not None else list(RiskDimension)
    raw = _score_examples(backend, examples, dims)
    probabilities = _probability_matrix(raw, dims, calibrators)
    if on_scored is not None:
        on_scored(raw, probabilities)

    threshold_selection = (
        _build_threshold_selection(
            backend,
            threshold_selection_examples,
            dims,
            calibrators,
            precomputed=threshold_selection_scores,
            on_scored=on_threshold_selection_scored,
        )
        if threshold_selection_examples
        else None
    )

    all_indices = list(range(len(examples)))
    dimension_metrics = _dimension_metrics_for_indices(
        examples,
        probabilities,
        dims,
        all_indices,
        threshold=threshold,
        threshold_selection=threshold_selection,
    )
    dimension_metrics = _attach_bootstrap_cis(
        examples,
        dimension_metrics,
        probabilities,
        threshold=threshold,
        seed=seed,
        n_boot=n_boot,
        ci_metrics=ci_metrics,
    )

    macro = {name: macro_average(dimension_metrics, name) for name in macro_metrics}

    all_slices = list(_default_slices(examples, training_tool_names)) + list(extra_slices)
    slice_reports: list[SliceReport] = []
    for sl in all_slices:
        idx = sl.select(examples)
        if not idx:
            continue
        dims_for_slice = _dimension_metrics_for_indices(
            examples, probabilities, dims, idx, threshold=threshold, threshold_selection=None
        )
        slice_reports.append(SliceReport(name=sl.name, n=len(idx), dimensions=dims_for_slice))

    worst_slice_by_metric = {
        name: slices.worst_slice(_ReportView(slice_reports), name) for name in macro_metrics
    }

    probability_by_example: dict[str, dict[RiskDimension, float | None]] = {
        e.example_id: {d: probabilities[d][i] for d in dims} for i, e in enumerate(examples)
    }
    consistency_report = ConsistencyReport(
        pair_consistency=consistency.pair_consistency(examples, probability_by_example),
        counterfactual_sensitivity=consistency.counterfactual_sensitivity(
            examples, probability_by_example
        ),
        invariance=consistency.invariance(examples, probability_by_example),
    )

    selective_results: dict[RiskDimension, SelectiveResult] = {}
    for dimension in dims:
        labels = [e.labels.values[dimension] for e in examples]
        probs = probabilities[dimension]
        y_true, y_prob, _ = extract_dimension_arrays(labels, probs)
        selective_results[dimension] = selective.selective_risk_coverage(
            y_true, y_prob, threshold=threshold
        )

    calibration_info = _calibration_info(calibrator_bundle, dims)

    responses = None
    decision_result = None
    if engine is not None:
        responses = _build_classify_responses(
            examples, raw, probabilities, dims, backend.model_info, calibration_info
        )
        decision_result = decisions_mod.decision_metrics(engine, responses, examples)

    stacking_result = None
    stack_policies = list(stacking_bundles)
    if stacking_synthetic:
        tau = {
            dimension: metrics.optimal_threshold
            for dimension, metrics in dimension_metrics.items()
            if metrics.optimal_threshold is not None
        }
        stack_policies += stacking_mod.synthetic_dimension_policies(
            thresholds=tau, default_threshold=threshold
        )
    if stack_policies:
        if responses is None:
            responses = _build_classify_responses(
                examples, raw, probabilities, dims, backend.model_info, calibration_info
            )
        stacking_result = stacking_mod.stacking_report(examples, responses, stack_policies)

    approval_elimination_result: ApprovalElimination | None = None
    if approval_curve_engine is not None and calibrators is None:
        logger.warning("skipping approval curve: no calibration bundle, scores are uncalibrated")
    elif approval_curve_engine is not None:
        if responses is None:
            responses = _build_classify_responses(
                examples, raw, probabilities, dims, backend.model_info, calibration_info
            )
        approval_elimination_result = approval_elimination_curve(
            approval_curve_engine,
            responses,
            examples,
            target_base_rate=approval_target_base_rate,
            incident_rate_mode=approval_incident_rate_mode,
        )

    latency_report: LatencyReport | None = None
    if include_latency:
        latency_report = measure_latency(backend, examples)

    split = examples[0].split if examples else None
    threshold_selection_split = (
        threshold_selection_examples[0].split if threshold_selection_examples else None
    )
    return EvaluationReport(
        evaluation_class=evaluation_class,
        dataset=DatasetIdentity(split=split, n=len(examples), sha256=dataset_sha256),
        model=backend.model_info,
        calibration=calibration_info,
        seed=seed,
        created_at=datetime.now(UTC),
        identity_stripped=identity_stripped,
        labels_source=labels_source,
        threshold_selection_split=threshold_selection_split,
        dimensions=dimension_metrics,
        macro=macro,
        worst_slice=worst_slice_by_metric,
        slices=slice_reports,
        consistency=consistency_report,
        selective=selective_results,
        decisions=decision_result,
        latency=latency_report,
        stacking=stacking_result,
        approval_elimination=approval_elimination_result,
    )
