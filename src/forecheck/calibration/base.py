"""Calibrator protocol and the artifact format that travels beside model weights.

A softmax value is not a probability. Everything in forecheck that claims to be a
probability comes out of a calibrator fitted on a dedicated calibration split that was
used for nothing else — not training, not model selection, not threshold search.
"""

from __future__ import annotations

import abc
from datetime import datetime
from typing import TYPE_CHECKING, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field

from forecheck.contracts import CalibrationMethod, RiskDimension

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray

__all__ = ["Calibrator", "CalibratorBundle", "DimensionCalibration", "FitReport"]


class DimensionCalibration(BaseModel):
    """Fitted parameters for one dimension, serialisable to JSON."""

    model_config = ConfigDict(extra="forbid")

    dimension: RiskDimension
    method: CalibrationMethod
    params: dict[str, list[float]] = Field(default_factory=dict)
    n_fit: int = Field(ge=0)
    n_positive: int = Field(ge=0)
    ece_before: float | None = None
    ece_after: float | None = None
    brier_before: float | None = None
    brier_after: float | None = None
    degenerate: bool = Field(
        default=False,
        description="True when the split had too few positives to fit. The dimension "
        "then reports abstention rather than a fabricated probability.",
    )


class CalibratorBundle(BaseModel):
    """All per-dimension calibrations plus the provenance that makes them auditable."""

    model_config = ConfigDict(extra="forbid")

    artifact_id: str
    backend_model_id: str
    prompt_contract_hash: str
    label_schema_version: str
    split_name: str
    dataset_sha256: str
    fitted_at: datetime
    forecheck_version: str
    dimensions: dict[RiskDimension, DimensionCalibration] = Field(default_factory=dict)


class FitReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bundle: CalibratorBundle
    macro_ece_before: float
    macro_ece_after: float
    macro_brier_before: float
    macro_brier_after: float
    warnings: list[str] = Field(default_factory=list)


@runtime_checkable
class Calibrator(Protocol):
    method: CalibrationMethod

    def fit(self, scores: NDArray[np.float64], labels: NDArray[np.int_]) -> None: ...

    def transform(self, scores: NDArray[np.float64]) -> NDArray[np.float64]: ...

    def to_params(self) -> dict[str, list[float]]: ...

    @classmethod
    def from_params(cls, params: dict[str, list[float]]) -> Calibrator: ...


class BaseCalibrator(abc.ABC):
    method: CalibrationMethod = CalibrationMethod.NONE

    @abc.abstractmethod
    def fit(self, scores: NDArray[np.float64], labels: NDArray[np.int_]) -> None: ...

    @abc.abstractmethod
    def transform(self, scores: NDArray[np.float64]) -> NDArray[np.float64]: ...

    @abc.abstractmethod
    def to_params(self) -> dict[str, list[float]]: ...

    @classmethod
    @abc.abstractmethod
    def from_params(cls, params: dict[str, list[float]]) -> BaseCalibrator: ...
