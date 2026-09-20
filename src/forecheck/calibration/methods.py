"""Calibration methods: score -> probability mappings fitted per risk dimension.

Every raw score here is treated as a pre-sigmoid logit: ``TemperatureScaling`` and
``VectorScaling`` apply ``sigmoid`` after an affine transform, and ``BetaCalibration``
applies ``sigmoid`` first to obtain a base probability before its own affine-in-log-odds
step. ``IsotonicCalibration`` makes no such assumption; it fits a monotonic mapping
directly on the raw score.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
from scipy.optimize import minimize
from sklearn.isotonic import IsotonicRegression

from forecheck.calibration.base import BaseCalibrator
from forecheck.contracts import CalibrationMethod

if TYPE_CHECKING:
    from numpy.typing import NDArray

__all__ = [
    "BetaCalibration",
    "IsotonicCalibration",
    "TemperatureScaling",
    "VectorScaling",
    "calibrator_for_method",
]

_EPS = 1e-12


def _sigmoid(x: NDArray[np.float64]) -> NDArray[np.float64]:
    return 1.0 / (1.0 + np.exp(-x))


def _clip_prob(p: NDArray[np.float64]) -> NDArray[np.float64]:
    return np.clip(p, _EPS, 1.0 - _EPS)


def _nll(probs: NDArray[np.float64], labels: NDArray[np.int_]) -> float:
    p = _clip_prob(probs)
    y = labels.astype(np.float64)
    return float(-np.mean(y * np.log(p) + (1.0 - y) * np.log(1.0 - p)))


class TemperatureScaling(BaseCalibrator):
    """``p = sigmoid(score / T)`` with a single scalar ``T > 0`` fitted by NLL."""

    method = CalibrationMethod.TEMPERATURE

    def __init__(self, temperature: float = 1.0) -> None:
        self._t = temperature

    def fit(self, scores: NDArray[np.float64], labels: NDArray[np.int_]) -> None:
        def loss(params: NDArray[np.float64]) -> float:
            t = max(params[0], _EPS)
            return _nll(_sigmoid(scores / t), labels)

        result = minimize(loss, x0=np.array([1.0]), method="Nelder-Mead")
        self._t = float(result.x[0]) if result.success and result.x[0] > 0 else 1.0

    def transform(self, scores: NDArray[np.float64]) -> NDArray[np.float64]:
        return _sigmoid(scores / self._t)

    def to_params(self) -> dict[str, list[float]]:
        return {"temperature": [self._t]}

    @classmethod
    def from_params(cls, params: dict[str, list[float]]) -> TemperatureScaling:
        return cls(temperature=params["temperature"][0])


class VectorScaling(BaseCalibrator):
    """``p = sigmoid(a * score + b)``, a per-dimension affine (Platt-style) fit."""

    method = CalibrationMethod.VECTOR

    def __init__(self, a: float = 1.0, b: float = 0.0) -> None:
        self._a = a
        self._b = b

    def fit(self, scores: NDArray[np.float64], labels: NDArray[np.int_]) -> None:
        def loss(params: NDArray[np.float64]) -> float:
            a, b = params
            return _nll(_sigmoid(a * scores + b), labels)

        result = minimize(loss, x0=np.array([1.0, 0.0]), method="Nelder-Mead")
        if result.success:
            self._a, self._b = float(result.x[0]), float(result.x[1])

    def transform(self, scores: NDArray[np.float64]) -> NDArray[np.float64]:
        return _sigmoid(self._a * scores + self._b)

    def to_params(self) -> dict[str, list[float]]:
        return {"a": [self._a], "b": [self._b]}

    @classmethod
    def from_params(cls, params: dict[str, list[float]]) -> VectorScaling:
        return cls(a=params["a"][0], b=params["b"][0])


class IsotonicCalibration(BaseCalibrator):
    """Non-parametric monotonic mapping via ``sklearn.isotonic.IsotonicRegression``."""

    method = CalibrationMethod.ISOTONIC

    def __init__(self) -> None:
        self._model = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)
        self._fitted = False

    def fit(self, scores: NDArray[np.float64], labels: NDArray[np.int_]) -> None:
        self._model.fit(scores, labels.astype(np.float64))
        self._fitted = True

    def transform(self, scores: NDArray[np.float64]) -> NDArray[np.float64]:
        if not self._fitted:
            raise RuntimeError("IsotonicCalibration.transform called before fit/from_params")
        result: NDArray[np.float64] = self._model.predict(scores)
        return result

    def to_params(self) -> dict[str, list[float]]:
        if not self._fitted:
            raise RuntimeError("IsotonicCalibration.to_params called before fit")
        return {
            "x_thresholds": list(self._model.X_thresholds_.astype(float)),
            "y_thresholds": list(self._model.y_thresholds_.astype(float)),
        }

    @classmethod
    def from_params(cls, params: dict[str, list[float]]) -> IsotonicCalibration:
        instance = cls()
        x = np.asarray(params["x_thresholds"], dtype=np.float64)
        y = np.asarray(params["y_thresholds"], dtype=np.float64)
        instance._model.increasing_ = True
        instance._model.X_thresholds_ = x
        instance._model.y_thresholds_ = y
        instance._model.X_min_, instance._model.X_max_ = float(x.min()), float(x.max())
        instance._model._build_f(x, y)
        instance._fitted = True
        return instance


class BetaCalibration(BaseCalibrator):
    """Beta calibration (Kull, Silva Filho & Flach, 2017).

    ``s = sigmoid(score)`` is treated as a base probability, then
    ``p = sigmoid(a * ln(s) - b * ln(1 - s) + c)``.
    """

    method = CalibrationMethod.BETA

    def __init__(self, a: float = 1.0, b: float = 1.0, c: float = 0.0) -> None:
        self._a = a
        self._b = b
        self._c = c

    def fit(self, scores: NDArray[np.float64], labels: NDArray[np.int_]) -> None:
        s = _clip_prob(_sigmoid(scores))
        log_s = np.log(s)
        log_1_minus_s = np.log(1.0 - s)

        def loss(params: NDArray[np.float64]) -> float:
            a, b, c = params
            return _nll(_sigmoid(a * log_s - b * log_1_minus_s + c), labels)

        result = minimize(loss, x0=np.array([1.0, 1.0, 0.0]), method="Nelder-Mead")
        if result.success:
            self._a, self._b, self._c = (float(v) for v in result.x)

    def transform(self, scores: NDArray[np.float64]) -> NDArray[np.float64]:
        s = _clip_prob(_sigmoid(scores))
        return _sigmoid(self._a * np.log(s) - self._b * np.log(1.0 - s) + self._c)

    def to_params(self) -> dict[str, list[float]]:
        return {"a": [self._a], "b": [self._b], "c": [self._c]}

    @classmethod
    def from_params(cls, params: dict[str, list[float]]) -> BetaCalibration:
        return cls(a=params["a"][0], b=params["b"][0], c=params["c"][0])


_REGISTRY: dict[CalibrationMethod, type[BaseCalibrator]] = {
    CalibrationMethod.TEMPERATURE: TemperatureScaling,
    CalibrationMethod.VECTOR: VectorScaling,
    CalibrationMethod.ISOTONIC: IsotonicCalibration,
    CalibrationMethod.BETA: BetaCalibration,
}


def calibrator_for_method(method: CalibrationMethod) -> type[BaseCalibrator]:
    if method not in _REGISTRY:
        raise ValueError(f"no calibrator implementation registered for method {method!r}")
    return _REGISTRY[method]
