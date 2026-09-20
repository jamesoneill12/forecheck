"""Fits a :class:`~forecheck.calibration.base.CalibratorBundle` on a calibration split.

``LabelValue.NOT_APPLICABLE`` and ``LabelValue.UNDETERMINED`` cells are skipped rather
than folded into either class: a read-only action legitimately has no destination, and
counting that as a negative ``untrusted_destination`` example would inflate precision
on the rare positives that matter. A dimension with fewer than ``min_positives``
positive examples, or with only one observed class, is marked ``degenerate`` and
reported in ``warnings`` instead of being fit on data too thin to trust.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime

import numpy as np

from forecheck.calibration.base import CalibratorBundle, DimensionCalibration, FitReport
from forecheck.calibration.methods import calibrator_for_method
from forecheck.calibration.metrics import brier_score, expected_calibration_error
from forecheck.contracts import LABEL_SCHEMA_VERSION, CalibrationMethod, LabelValue, RiskDimension
from forecheck.version import __version__

__all__ = ["fit_bundle"]

_SKIPPED_LABELS = frozenset({LabelValue.NOT_APPLICABLE, LabelValue.UNDETERMINED})


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-x))


def _filter(scores: Sequence[float], labels: Sequence[LabelValue]) -> tuple[np.ndarray, np.ndarray]:
    kept_scores: list[float] = []
    kept_labels: list[int] = []
    for score, label in zip(scores, labels, strict=True):
        if label in _SKIPPED_LABELS:
            continue
        kept_scores.append(score)
        kept_labels.append(1 if label is LabelValue.YES else 0)
    return np.asarray(kept_scores, dtype=np.float64), np.asarray(kept_labels, dtype=np.int_)


def fit_bundle(
    scores: Mapping[RiskDimension, Sequence[float]],
    labels: Mapping[RiskDimension, Sequence[LabelValue]],
    method: CalibrationMethod,
    *,
    backend_model_id: str,
    prompt_contract_hash: str,
    dataset_sha256: str,
    split_name: str = "calibration",
    min_positives: int = 25,
    artifact_id: str | None = None,
) -> FitReport:
    dimensions: dict[RiskDimension, DimensionCalibration] = {}
    warnings: list[str] = []
    fitted_eces_before: list[float] = []
    fitted_eces_after: list[float] = []
    fitted_briers_before: list[float] = []
    fitted_briers_after: list[float] = []

    for dimension in RiskDimension:
        if dimension not in scores or dimension not in labels:
            continue
        s, y = _filter(scores[dimension], labels[dimension])
        n_fit = int(y.size)
        n_positive = int(np.sum(y)) if n_fit else 0
        n_classes = int(np.unique(y).size) if n_fit else 0
        degenerate = n_fit == 0 or n_positive < min_positives or n_classes < 2

        if degenerate:
            warnings.append(
                f"{dimension.value}: degenerate calibration split "
                f"(n_fit={n_fit}, n_positive={n_positive}, n_classes={n_classes}); "
                "abstaining instead of fitting"
            )
            dimensions[dimension] = DimensionCalibration(
                dimension=dimension,
                method=CalibrationMethod.NONE,
                params={},
                n_fit=n_fit,
                n_positive=n_positive,
                degenerate=True,
            )
            continue

        baseline = np.clip(_sigmoid(s), 1e-12, 1.0 - 1e-12)
        ece_before = expected_calibration_error(baseline, y)
        brier_before = brier_score(baseline, y)

        calibrator = calibrator_for_method(method)()
        calibrator.fit(s, y)
        calibrated = np.clip(calibrator.transform(s), 0.0, 1.0)
        ece_after = expected_calibration_error(calibrated, y)
        brier_after = brier_score(calibrated, y)

        dimensions[dimension] = DimensionCalibration(
            dimension=dimension,
            method=method,
            params=calibrator.to_params(),
            n_fit=n_fit,
            n_positive=n_positive,
            ece_before=ece_before,
            ece_after=ece_after,
            brier_before=brier_before,
            brier_after=brier_after,
            degenerate=False,
        )
        fitted_eces_before.append(ece_before)
        fitted_eces_after.append(ece_after)
        fitted_briers_before.append(brier_before)
        fitted_briers_after.append(brier_after)

    if not fitted_eces_after:
        warnings.append("no dimension had enough data to fit; bundle is entirely degenerate")

    bundle = CalibratorBundle(
        artifact_id=artifact_id or str(uuid.uuid4()),
        backend_model_id=backend_model_id,
        prompt_contract_hash=prompt_contract_hash,
        label_schema_version=LABEL_SCHEMA_VERSION,
        split_name=split_name,
        dataset_sha256=dataset_sha256,
        fitted_at=datetime.now(UTC),
        forecheck_version=__version__,
        dimensions=dimensions,
    )
    return FitReport(
        bundle=bundle,
        macro_ece_before=_mean_or_zero(fitted_eces_before),
        macro_ece_after=_mean_or_zero(fitted_eces_after),
        macro_brier_before=_mean_or_zero(fitted_briers_before),
        macro_brier_after=_mean_or_zero(fitted_briers_after),
        warnings=warnings,
    )


def _mean_or_zero(values: list[float]) -> float:
    return float(np.mean(values)) if values else 0.0
