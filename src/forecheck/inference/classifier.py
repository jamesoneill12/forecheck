"""The classifier facade: backend + optional calibrator bundle -> ClassifyResponse.

This is where forecheck's central honesty guarantee lives: without a loaded
calibration bundle, nothing produced here is allowed to look like a probability.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

from forecheck.calibration.methods import calibrator_for_method
from forecheck.contracts import (
    AbstentionReason,
    CalibrationInfo,
    CalibrationMethod,
    ClassifyResponse,
    DimensionScore,
    RiskDimension,
)
from forecheck.inference.prompt import prompt_contract_hash

if TYPE_CHECKING:
    from forecheck.calibration.base import BaseCalibrator, CalibratorBundle
    from forecheck.contracts import ClassifyRequest
    from forecheck.inference.base import ClassifierBackend, RawScores

__all__ = ["AbstainPolicy", "Classifier"]


@dataclass(frozen=True, slots=True)
class AbstainPolicy:
    """Thresholds governing when a dimension or a whole response abstains.

    ``max_interval_width`` bounds an approximate predictive interval built from the
    calibrator's own measured calibration error (``p +/- ece_after``), since the
    calibrator implementations here are point estimators and do not fit a genuine
    predictive distribution. ``insufficient_context_threshold`` only applies when
    ``insufficient_context`` is calibrated; an uncalibrated raw score is not on a
    known probability scale and is never compared to it.
    """

    max_interval_width: float = 0.6
    insufficient_context_threshold: float = 0.7


class Classifier:
    def __init__(
        self,
        backend: ClassifierBackend,
        calibrator_bundle: CalibratorBundle | None = None,
        *,
        abstain_policy: AbstainPolicy | None = None,
    ) -> None:
        self._backend = backend
        self._bundle = calibrator_bundle
        self._abstain_policy = abstain_policy or AbstainPolicy()
        self._calibrators: dict[RiskDimension, BaseCalibrator] = {}
        if calibrator_bundle is not None:
            self._validate_bundle(calibrator_bundle, backend)
            for dimension, dim_cal in calibrator_bundle.dimensions.items():
                if dim_cal.degenerate:
                    continue
                self._calibrators[dimension] = calibrator_for_method(dim_cal.method).from_params(
                    dim_cal.params
                )

    @staticmethod
    def _validate_bundle(bundle: CalibratorBundle, backend: ClassifierBackend) -> None:
        if bundle.prompt_contract_hash != prompt_contract_hash():
            raise ValueError(
                "calibration bundle prompt_contract_hash "
                f"{bundle.prompt_contract_hash!r} does not match the running prompt "
                f"contract {prompt_contract_hash()!r}"
            )
        if bundle.backend_model_id != backend.model_info.model_id:
            raise ValueError(
                f"calibration bundle backend_model_id {bundle.backend_model_id!r} does "
                f"not match the loaded backend {backend.model_info.model_id!r}"
            )

    def classify(self, request: ClassifyRequest) -> ClassifyResponse:
        start = time.perf_counter()
        raw = self._backend.score(request.context, request.options.dimensions)
        return self.classify_from_raw(request, raw, start=start)

    def classify_from_raw(
        self, request: ClassifyRequest, raw: RawScores, start: float | None = None
    ) -> ClassifyResponse:
        """Apply calibration and abstention to scores already computed by the backend.

        Lets a caller that has already batched raw scoring (e.g. the API's batch route)
        still go through exactly the same calibration/abstention logic as :meth:`classify`.
        """
        started = time.perf_counter() if start is None else start
        requested_dims = request.options.dimensions
        dims = requested_dims if requested_dims is not None else list(RiskDimension)

        scores: list[DimensionScore] = []
        abstention_reasons: set[AbstentionReason] = set()
        response_abstained = False

        for dimension in dims:
            raw_value = raw.scores.get(dimension)
            if raw_value is None:
                continue
            score, reason = self._score_dimension(dimension, raw_value, raw, request)
            scores.append(score)
            if reason is not None:
                abstention_reasons.add(reason)
            if (
                dimension is RiskDimension.INSUFFICIENT_CONTEXT
                and score.probability is not None
                and score.probability >= self._abstain_policy.insufficient_context_threshold
            ):
                response_abstained = True
                abstention_reasons.add(AbstentionReason.MISSING_REQUIRED_CONTEXT)

        calibration_info = self._calibration_info()
        latency_ms = (time.perf_counter() - started) * 1000.0
        return ClassifyResponse(
            request_id=request.request_id,
            scores=scores,
            model=self._backend.model_info,
            calibration=calibration_info,
            truncation=raw.truncation,
            abstained=response_abstained,
            abstention_reasons=sorted(abstention_reasons, key=lambda r: r.value),
            latency_ms=latency_ms,
        )

    def _score_dimension(
        self,
        dimension: RiskDimension,
        raw_value: float,
        raw: RawScores,
        request: ClassifyRequest,
    ) -> tuple[DimensionScore, AbstentionReason | None]:
        include_raw = request.options.include_uncalibrated
        raw_score_out = raw_value if include_raw else None

        if dimension in raw.abstained_dimensions:
            return (
                DimensionScore(
                    dimension=dimension,
                    probability=None,
                    raw_score=raw_score_out,
                    calibrated=False,
                    abstained=True,
                ),
                AbstentionReason.LOW_CONFIDENCE,
            )

        if self._bundle is None or dimension not in self._bundle.dimensions:
            return (
                DimensionScore(
                    dimension=dimension,
                    probability=None,
                    raw_score=raw_score_out,
                    calibrated=False,
                    abstained=False,
                ),
                None,
            )

        dim_cal = self._bundle.dimensions[dimension]
        if dim_cal.degenerate or dimension not in self._calibrators:
            return (
                DimensionScore(
                    dimension=dimension,
                    probability=None,
                    raw_score=raw_score_out,
                    calibrated=False,
                    abstained=True,
                ),
                AbstentionReason.LOW_CONFIDENCE,
            )

        calibrator = self._calibrators[dimension]
        probability = float(calibrator.transform(np.array([raw_value], dtype=np.float64))[0])
        probability = min(1.0, max(0.0, probability))
        half_width = dim_cal.ece_after if dim_cal.ece_after is not None else 0.0
        interval = (max(0.0, probability - half_width), min(1.0, probability + half_width))
        if (interval[1] - interval[0]) > self._abstain_policy.max_interval_width:
            return (
                DimensionScore(
                    dimension=dimension,
                    probability=None,
                    raw_score=raw_score_out,
                    calibrated=False,
                    abstained=True,
                ),
                AbstentionReason.LOW_CONFIDENCE,
            )
        return (
            DimensionScore(
                dimension=dimension,
                probability=probability,
                raw_score=raw_score_out,
                calibrated=True,
                abstained=False,
                interval=interval,
            ),
            None,
        )

    def _calibration_info(self) -> CalibrationInfo:
        if self._bundle is None:
            return CalibrationInfo(method=CalibrationMethod.NONE)
        eces = [d.ece_after for d in self._bundle.dimensions.values() if d.ece_after is not None]
        macro_ece = sum(eces) / len(eces) if eces else None
        fitted_methods = [
            d.method
            for d in self._bundle.dimensions.values()
            if d.method is not CalibrationMethod.NONE
        ]
        method = fitted_methods[0] if fitted_methods else CalibrationMethod.NONE
        return CalibrationInfo(
            method=method,
            artifact_id=self._bundle.artifact_id,
            fitted_at=self._bundle.fitted_at,
            fitted_on_split=self._bundle.split_name,
            fitted_on_n=None,
            dataset_hash=self._bundle.dataset_sha256,
            expected_calibration_error=macro_ece,
        )
