from __future__ import annotations

import numpy as np
import pytest

from forecheck.calibration.methods import (
    BetaCalibration,
    IsotonicCalibration,
    TemperatureScaling,
    VectorScaling,
    calibrator_for_method,
)
from forecheck.contracts import CalibrationMethod


def _synthetic_logits(n: int, seed: int) -> tuple[np.ndarray, np.ndarray]:
    rng = np.random.default_rng(seed)
    true_logits = rng.normal(0.0, 2.0, size=n)
    probs = 1.0 / (1.0 + np.exp(-true_logits))
    labels = rng.binomial(1, probs)
    miscalibrated = true_logits * 3.0 + 1.0
    return miscalibrated, labels


@pytest.mark.parametrize(
    "cls", [TemperatureScaling, VectorScaling, IsotonicCalibration, BetaCalibration]
)
def test_round_trip_to_params_from_params_preserves_transform(cls: type) -> None:
    scores, labels = _synthetic_logits(200, seed=1)
    calibrator = cls()
    calibrator.fit(scores, labels)
    before = calibrator.transform(scores)

    params = calibrator.to_params()
    restored = cls.from_params(params)
    after = restored.transform(scores)

    np.testing.assert_allclose(before, after, atol=1e-9)
    assert restored.to_params() == pytest.approx(params)


def test_calibrator_for_method_returns_matching_class() -> None:
    assert calibrator_for_method(CalibrationMethod.TEMPERATURE) is TemperatureScaling
    assert calibrator_for_method(CalibrationMethod.VECTOR) is VectorScaling
    assert calibrator_for_method(CalibrationMethod.ISOTONIC) is IsotonicCalibration
    assert calibrator_for_method(CalibrationMethod.BETA) is BetaCalibration


def test_calibrator_for_method_rejects_none() -> None:
    with pytest.raises(ValueError, match="no calibrator implementation"):
        calibrator_for_method(CalibrationMethod.NONE)


def test_temperature_scaling_outputs_are_valid_probabilities() -> None:
    scores, labels = _synthetic_logits(300, seed=2)
    calibrator = TemperatureScaling()
    calibrator.fit(scores, labels)
    probs = calibrator.transform(scores)
    assert np.all((probs >= 0.0) & (probs <= 1.0))


def test_vector_scaling_reduces_nll_versus_raw_sigmoid() -> None:
    scores, labels = _synthetic_logits(400, seed=3)
    raw_probs = 1.0 / (1.0 + np.exp(-scores))
    calibrator = VectorScaling()
    calibrator.fit(scores, labels)
    calibrated_probs = calibrator.transform(scores)

    def nll(p: np.ndarray) -> float:
        clipped = np.clip(p, 1e-12, 1 - 1e-12)
        return float(-np.mean(labels * np.log(clipped) + (1 - labels) * np.log(1 - clipped)))

    assert nll(calibrated_probs) <= nll(raw_probs)


def test_isotonic_is_monotonic_nondecreasing() -> None:
    scores, labels = _synthetic_logits(300, seed=4)
    calibrator = IsotonicCalibration()
    calibrator.fit(scores, labels)
    order = np.argsort(scores)
    probs = calibrator.transform(scores[order])
    assert np.all(np.diff(probs) >= -1e-9)


def test_isotonic_transform_before_fit_raises() -> None:
    calibrator = IsotonicCalibration()
    with pytest.raises(RuntimeError):
        calibrator.transform(np.array([0.1, 0.2]))
