"""Backend protocol for scoring atomic risk dimensions.

A backend returns *raw scores* only. It must not calibrate, threshold, or decide.
Calibration is applied by :mod:`forecheck.calibration`; decisions are made by
:mod:`forecheck.policies`. Keeping raw scoring behind this narrow protocol is what
lets the mock backend, the Hugging Face backend and any future backend be swapped
without touching the service or the policy layer.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from collections.abc import Sequence

    from forecheck.contracts import ActionContext, ModelInfo, RiskDimension, TruncationInfo

__all__ = ["BackendCapabilities", "ClassifierBackend", "RawScores"]


@dataclass(frozen=True, slots=True)
class RawScores:
    """Uncalibrated per-dimension scores for one action.

    ``scores`` are on whatever scale the backend produces (log-odds for the
    candidate-logit backend, [0, 1] for the mock). Only the calibrator is permitted to
    interpret them, and only after being fitted on the same backend.
    """

    scores: dict[RiskDimension, float]
    truncation: TruncationInfo
    abstained_dimensions: frozenset[RiskDimension] = field(default_factory=frozenset)
    prompt_tokens: int | None = None


@dataclass(frozen=True, slots=True)
class BackendCapabilities:
    supports_batching: bool = False
    supports_shared_prefill: bool = False
    max_prompt_tokens: int = 8192
    device: str = "cpu"
    deterministic: bool = True


@runtime_checkable
class ClassifierBackend(Protocol):
    """Anything that can turn an :class:`ActionContext` into raw dimension scores."""

    @property
    def model_info(self) -> ModelInfo: ...

    @property
    def capabilities(self) -> BackendCapabilities: ...

    def score(
        self, context: ActionContext, dimensions: Sequence[RiskDimension] | None = None
    ) -> RawScores: ...

    def score_batch(
        self,
        contexts: Sequence[ActionContext],
        dimensions: Sequence[RiskDimension] | None = None,
    ) -> list[RawScores]: ...

    def warmup(self) -> None: ...

    def close(self) -> None: ...


class BaseBackend(abc.ABC):
    """Convenience base supplying a correct sequential ``score_batch`` and no-op
    lifecycle methods. Backends with real batching override ``score_batch``."""

    @property
    @abc.abstractmethod
    def model_info(self) -> ModelInfo: ...

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities()

    @abc.abstractmethod
    def score(
        self, context: ActionContext, dimensions: Sequence[RiskDimension] | None = None
    ) -> RawScores: ...

    def score_batch(
        self,
        contexts: Sequence[ActionContext],
        dimensions: Sequence[RiskDimension] | None = None,
    ) -> list[RawScores]:
        return [self.score(c, dimensions) for c in contexts]

    def warmup(self) -> None:
        return None

    def close(self) -> None:
        return None
