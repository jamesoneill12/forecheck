"""Fits, applies, and persists per-dimension score-to-probability calibrations."""

from __future__ import annotations

from forecheck.calibration.base import (
    BaseCalibrator,
    Calibrator,
    CalibratorBundle,
    DimensionCalibration,
    FitReport,
)
from forecheck.calibration.fit import fit_bundle
from forecheck.calibration.methods import (
    BetaCalibration,
    IsotonicCalibration,
    TemperatureScaling,
    VectorScaling,
    calibrator_for_method,
)
from forecheck.calibration.metrics import (
    ReliabilityCurve,
    adaptive_ece,
    brier_score,
    expected_calibration_error,
    negative_log_likelihood,
    reliability_curve,
)
from forecheck.calibration.store import load_bundle, save_bundle

__all__ = [
    "BaseCalibrator",
    "BetaCalibration",
    "Calibrator",
    "CalibratorBundle",
    "DimensionCalibration",
    "FitReport",
    "IsotonicCalibration",
    "ReliabilityCurve",
    "TemperatureScaling",
    "VectorScaling",
    "adaptive_ece",
    "brier_score",
    "calibrator_for_method",
    "expected_calibration_error",
    "fit_bundle",
    "load_bundle",
    "negative_log_likelihood",
    "reliability_curve",
    "save_bundle",
]
