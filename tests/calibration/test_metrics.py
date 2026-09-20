from __future__ import annotations

import numpy as np

from forecheck.calibration.methods import TemperatureScaling
from forecheck.calibration.metrics import (
    adaptive_ece,
    brier_score,
    expected_calibration_error,
    negative_log_likelihood,
    reliability_curve,
)


def _well_calibrated(n: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    probs = rng.uniform(0.01, 0.99, size=n)
    labels = rng.binomial(1, probs)
    return probs, labels


def _badly_miscalibrated(n: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    true_probs = rng.uniform(0.01, 0.99, size=n)
    labels = rng.binomial(1, true_probs)
    overconfident = np.clip(0.5 + (true_probs - 0.5) * 6.0, 0.001, 0.999)
    return overconfident, labels


def test_ece_near_zero_for_well_calibrated_distribution() -> None:
    probs, labels = _well_calibrated(20_000, seed=0)
    assert expected_calibration_error(probs, labels, n_bins=20) < 0.03


def test_ece_large_for_miscalibrated_distribution() -> None:
    probs, labels = _badly_miscalibrated(20_000, seed=1)
    assert expected_calibration_error(probs, labels, n_bins=20) > 0.1


def test_temperature_scaling_reduces_ece_on_miscalibrated_distribution() -> None:
    rng = np.random.default_rng(2)
    true_logits = rng.normal(0.0, 2.0, size=20_000)
    probs_true = 1.0 / (1.0 + np.exp(-true_logits))
    labels = rng.binomial(1, probs_true)
    overconfident_logits = true_logits * 4.0

    before = 1.0 / (1.0 + np.exp(-overconfident_logits))
    ece_before = expected_calibration_error(before, labels, n_bins=20)

    calibrator = TemperatureScaling()
    calibrator.fit(overconfident_logits, labels)
    after = calibrator.transform(overconfident_logits)
    ece_after = expected_calibration_error(after, labels, n_bins=20)

    assert ece_after < ece_before


def test_adaptive_ece_is_finite_and_bounded() -> None:
    probs, labels = _badly_miscalibrated(5_000, seed=3)
    value = adaptive_ece(probs, labels, n_bins=10)
    assert 0.0 <= value <= 1.0


def test_brier_score_is_zero_for_perfect_predictions() -> None:
    labels = np.array([0, 1, 1, 0])
    probs = labels.astype(float)
    assert brier_score(probs, labels) == 0.0


def test_negative_log_likelihood_penalizes_confident_wrong_predictions() -> None:
    labels = np.array([1, 1, 1])
    confident_right = np.array([0.99, 0.99, 0.99])
    confident_wrong = np.array([0.01, 0.01, 0.01])
    assert negative_log_likelihood(confident_right, labels) < negative_log_likelihood(
        confident_wrong, labels
    )


def test_reliability_curve_shapes_and_counts_sum() -> None:
    probs, labels = _well_calibrated(1000, seed=4)
    curve = reliability_curve(probs, labels, n_bins=10)
    assert curve.bin_centers.shape == (10,)
    assert curve.accuracies.shape == (10,)
    assert curve.counts.shape == (10,)
    assert int(np.sum(curve.counts)) == 1000


def test_metrics_handle_empty_input() -> None:
    empty = np.array([])
    assert expected_calibration_error(empty, empty) == 0.0
    assert adaptive_ece(empty, empty) == 0.0
    assert brier_score(empty, empty) == 0.0
    assert negative_log_likelihood(empty, empty) == 0.0
