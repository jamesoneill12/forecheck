from __future__ import annotations

import numpy as np
import pytest

from forecheck.contracts import LabelValue, RiskDimension
from forecheck.evaluation.metrics import (
    compute_dimension_metrics,
    expected_calibration_error,
    extract_dimension_arrays,
    find_f1_optimal_threshold,
    get_metric,
    macro_average,
    threshold_metrics,
)

DIM = RiskDimension.FINANCIAL_COMMITMENT


def test_extract_dimension_arrays_excludes_not_applicable_and_undetermined() -> None:
    labels = [LabelValue.YES, LabelValue.NO, LabelValue.NOT_APPLICABLE, LabelValue.UNDETERMINED]
    probs = [0.9, 0.1, 0.5, 0.5]
    y_true, y_prob, kept = extract_dimension_arrays(labels, probs)
    assert list(y_true) == [1, 0]
    assert list(y_prob) == [0.9, 0.1]
    assert list(kept) == [0, 1]


def test_extract_dimension_arrays_excludes_abstained_none_probability() -> None:
    labels = [LabelValue.YES, LabelValue.NO]
    probs = [0.9, None]
    y_true, _y_prob, kept = extract_dimension_arrays(labels, probs)
    assert list(kept) == [0]
    assert list(y_true) == [1]


def test_all_not_applicable_dimension_yields_n_evaluable_zero_not_perfect_score() -> None:
    labels = [LabelValue.NOT_APPLICABLE] * 5
    probs = [0.9, 0.1, 0.5, 0.0, 1.0]
    y_true, y_prob, _ = extract_dimension_arrays(labels, probs)
    metrics = compute_dimension_metrics(DIM, y_true, y_prob)
    assert metrics.n_evaluable == 0
    assert metrics.n_positive == 0
    assert metrics.positive_rate is None
    assert metrics.auprc is None
    assert metrics.auroc is None
    assert metrics.brier is None
    assert metrics.nll is None
    assert metrics.ece is None
    assert metrics.adaptive_ece is None
    assert metrics.reliability_bins == ()
    assert metrics.at_threshold is None
    assert metrics.at_optimal_threshold is None


def test_threshold_metrics_known_confusion_matrix() -> None:
    y_true = np.array([1, 1, 0, 0], dtype=np.int_)
    y_prob = np.array([0.9, 0.4, 0.6, 0.1], dtype=np.float64)
    m = threshold_metrics(y_true, y_prob, 0.5)
    assert m.precision == pytest.approx(0.5)
    assert m.recall == pytest.approx(0.5)
    assert m.f1 == pytest.approx(0.5)


def test_threshold_metrics_default_is_point_five() -> None:
    y_true = np.array([1, 0], dtype=np.int_)
    y_prob = np.array([0.5, 0.4], dtype=np.float64)
    metrics = compute_dimension_metrics(DIM, y_true, y_prob)
    assert metrics.at_threshold is not None
    assert metrics.at_threshold.threshold == 0.5


def test_find_f1_optimal_threshold_uses_separate_array_not_eval_array() -> None:
    selection_true = np.array([1, 1, 0, 0], dtype=np.int_)
    selection_prob = np.array([0.9, 0.8, 0.3, 0.2], dtype=np.float64)
    eval_true = np.array([1, 0], dtype=np.int_)
    eval_prob = np.array([0.85, 0.25], dtype=np.float64)
    metrics = compute_dimension_metrics(
        DIM,
        eval_true,
        eval_prob,
        threshold_selection_true=selection_true,
        threshold_selection_prob=selection_prob,
    )
    assert metrics.optimal_threshold is not None
    assert metrics.at_optimal_threshold is not None
    found = find_f1_optimal_threshold(selection_true, selection_prob)
    assert found is not None
    assert metrics.optimal_threshold == pytest.approx(found[0])


def test_find_f1_optimal_threshold_single_class_returns_none() -> None:
    y_true = np.array([1, 1, 1], dtype=np.int_)
    y_prob = np.array([0.9, 0.8, 0.7], dtype=np.float64)
    assert find_f1_optimal_threshold(y_true, y_prob) is None


def test_auprc_auroc_none_when_single_class() -> None:
    y_true = np.array([1, 1, 1], dtype=np.int_)
    y_prob = np.array([0.9, 0.8, 0.7], dtype=np.float64)
    metrics = compute_dimension_metrics(DIM, y_true, y_prob)
    assert metrics.auprc is None
    assert metrics.auroc is None
    assert metrics.brier is not None
    assert metrics.n_evaluable == 3


def test_perfectly_calibrated_bins_have_zero_ece() -> None:
    rng = np.random.default_rng(0)
    y_prob = rng.uniform(0, 1, size=2000)
    y_true = (rng.uniform(0, 1, size=2000) < y_prob).astype(np.int_)
    metrics = compute_dimension_metrics(DIM, y_true, y_prob, n_bins=10)
    assert metrics.ece is not None
    assert metrics.ece < 0.05
    assert metrics.adaptive_ece is not None
    assert metrics.adaptive_ece < 0.05


def test_expected_calibration_error_empty_bins_is_none() -> None:
    assert expected_calibration_error([], 0) is None


def test_get_metric_unknown_name_raises() -> None:
    y_true = np.array([1, 0], dtype=np.int_)
    y_prob = np.array([0.9, 0.1], dtype=np.float64)
    metrics = compute_dimension_metrics(DIM, y_true, y_prob)
    with pytest.raises(KeyError):
        get_metric(metrics, "not-a-real-metric")


def test_macro_average_ignores_none_values() -> None:
    y_true_ok = np.array([1, 0], dtype=np.int_)
    y_prob_ok = np.array([0.9, 0.1], dtype=np.float64)
    y_true_na = np.array([], dtype=np.int_)
    y_prob_na = np.array([], dtype=np.float64)
    dims = {
        RiskDimension.FINANCIAL_COMMITMENT: compute_dimension_metrics(
            RiskDimension.FINANCIAL_COMMITMENT, y_true_ok, y_prob_ok
        ),
        RiskDimension.POLICY_CONFLICT: compute_dimension_metrics(
            RiskDimension.POLICY_CONFLICT, y_true_na, y_prob_na
        ),
    }
    value = macro_average(dims, "f1")
    assert value == pytest.approx(1.0)


def test_macro_average_all_none_returns_none() -> None:
    y_true_na = np.array([], dtype=np.int_)
    y_prob_na = np.array([], dtype=np.float64)
    dims = {
        RiskDimension.FINANCIAL_COMMITMENT: compute_dimension_metrics(
            RiskDimension.FINANCIAL_COMMITMENT, y_true_na, y_prob_na
        ),
    }
    assert macro_average(dims, "f1") is None
