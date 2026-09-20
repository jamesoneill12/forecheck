"""Versioned request and response envelopes for the forecheck API.

Layer separation is enforced here by types. :class:`ClassifyResponse` carries only
scores and provenance; it has no ``decision`` field. :class:`PolicyDecision` carries a
decision and the rule identifiers that produced it, and it is computed by deterministic
code that never calls the model.
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forecheck.contracts.context import ActionContext
from forecheck.contracts.enums import (
    AbstentionReason,
    CalibrationMethod,
    Decision,
    ObligationKind,
    RiskDimension,
    RuleKind,
)
from forecheck.contracts.limits import Limits

__all__ = [
    "SCHEMA_VERSION",
    "BatchClassifyRequest",
    "BatchClassifyResponse",
    "CalibrationInfo",
    "ClassifyOptions",
    "ClassifyRequest",
    "ClassifyResponse",
    "DimensionScore",
    "ModelInfo",
    "Obligation",
    "PolicyDecision",
    "PolicyEvaluateRequest",
    "RuleMatch",
    "TruncationInfo",
]

SchemaVersion = Literal["1.0"]
SCHEMA_VERSION: SchemaVersion = "1.0"

Probability = Annotated[float, Field(ge=0.0, le=1.0)]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, protected_namespaces=())


class ClassifyOptions(_Model):
    dimensions: list[RiskDimension] | None = Field(
        default=None, description="Subset to score. None scores all dimensions."
    )
    include_uncalibrated: bool = Field(
        default=False,
        description="Return the raw pre-calibration score alongside the probability. "
        "Off by default so that callers cannot accidentally threshold on raw scores.",
    )
    abstain_below_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    timeout_ms: int | None = Field(default=None, ge=1, le=60_000)


class ClassifyRequest(_Model):
    schema_version: SchemaVersion = SCHEMA_VERSION
    request_id: str | None = Field(default=None, max_length=Limits.SHORT_STR)
    context: ActionContext
    options: ClassifyOptions = Field(default_factory=ClassifyOptions)


class BatchClassifyRequest(_Model):
    schema_version: SchemaVersion = SCHEMA_VERSION
    items: list[ClassifyRequest] = Field(min_length=1, max_length=Limits.MAX_BATCH_ITEMS)


class ModelInfo(_Model):
    """Identifies exactly what produced a score, including the prompt contract.

    ``prompt_contract_hash`` pins the serialization of context into model input. A
    checkpoint evaluated under one prompt contract and served under another is a
    silent correctness bug, so the hash travels with every response.
    """

    backend: str
    model_id: str
    revision: str | None = None
    base_model: str | None = None
    adapter_id: str | None = None
    prompt_contract_hash: str
    label_schema_version: str
    quantization: str | None = None


class CalibrationInfo(_Model):
    """Provenance of the mapping from raw scores to probabilities.

    ``method == NONE`` means the returned numbers are **not** probabilities. Clients
    must treat them as ordinal only; the policy engine refuses probability thresholds
    in that state unless explicitly overridden.
    """

    method: CalibrationMethod = CalibrationMethod.NONE
    artifact_id: str | None = None
    fitted_at: datetime | None = None
    fitted_on_split: str | None = None
    fitted_on_n: int | None = Field(default=None, ge=0)
    dataset_hash: str | None = None
    expected_calibration_error: float | None = Field(default=None, ge=0.0, le=1.0)

    @property
    def is_calibrated(self) -> bool:
        return self.method is not CalibrationMethod.NONE


class DimensionScore(_Model):
    dimension: RiskDimension
    probability: Probability | None = Field(
        default=None,
        description="Calibrated probability. None when the model abstained on this "
        "dimension or no calibration artifact is loaded.",
    )
    raw_score: float | None = Field(
        default=None, description="Pre-calibration score; present only when requested."
    )
    calibrated: bool = False
    abstained: bool = False
    interval: tuple[Probability, Probability] | None = Field(
        default=None, description="Optional predictive interval from the calibrator."
    )

    @model_validator(mode="after")
    def _abstention_has_no_probability(self) -> DimensionScore:
        if self.abstained and self.probability is not None:
            raise ValueError("an abstained dimension must not carry a probability")
        if self.calibrated and self.probability is None and not self.abstained:
            raise ValueError("calibrated score must carry a probability")
        return self


class TruncationInfo(_Model):
    truncated: bool = False
    dropped_trajectory_steps: int = Field(default=0, ge=0)
    dropped_observations: int = Field(default=0, ge=0)
    dropped_characters: int = Field(default=0, ge=0)


class ClassifyResponse(_Model):
    schema_version: SchemaVersion = SCHEMA_VERSION
    request_id: str | None = None
    scores: list[DimensionScore]
    model: ModelInfo
    calibration: CalibrationInfo
    truncation: TruncationInfo = Field(default_factory=TruncationInfo)
    abstained: bool = False
    abstention_reasons: list[AbstentionReason] = Field(default_factory=list)
    latency_ms: float = Field(ge=0.0)

    def by_dimension(self) -> dict[RiskDimension, DimensionScore]:
        return {s.dimension: s for s in self.scores}

    def probability(self, dimension: RiskDimension) -> float | None:
        score = self.by_dimension().get(dimension)
        return None if score is None else score.probability


class BatchClassifyResponse(_Model):
    schema_version: SchemaVersion = SCHEMA_VERSION
    items: list[ClassifyResponse]


class Obligation(_Model):
    kind: ObligationKind
    detail: str | None = None


class RuleMatch(_Model):
    """One policy rule that fired, with the facts that made it fire."""

    rule_id: str
    decision: Decision
    description: str
    matched_on: dict[str, str] = Field(
        default_factory=dict,
        description="Typed fact name to its stringified value, e.g. "
        "{'prompt_injection_influence': '0.91', 'threshold': '0.60'}.",
    )
    obligations: list[Obligation] = Field(default_factory=list)
    hard: bool = Field(
        default=False,
        description="Mirrors the rule's 'hard' flag: an allow_override rule can never "
        "flip a decision that included a hard match, even on replay.",
    )
    kind: RuleKind = Field(
        default=RuleKind.STANDARD,
        description="Mirrors the rule's kind, so combining matched_rules alone (without "
        "the original bundle) reproduces the decision.",
    )


class PolicyEvaluateRequest(_Model):
    """Evaluate a policy bundle against scores.

    Accepts either an existing :class:`ClassifyResponse` (when the caller has already
    classified) or a full :class:`ActionContext` (the service classifies, then
    evaluates). Supplying both is rejected so the provenance of the scores is never
    ambiguous.
    """

    schema_version: SchemaVersion = SCHEMA_VERSION
    request_id: str | None = None
    policy_bundle_id: str | None = None
    classification: ClassifyResponse | None = None
    context: ActionContext | None = None

    @model_validator(mode="after")
    def _exactly_one_input(self) -> PolicyEvaluateRequest:
        if (self.classification is None) == (self.context is None):
            raise ValueError("supply exactly one of 'classification' or 'context'")
        return self


class PolicyDecision(_Model):
    schema_version: SchemaVersion = SCHEMA_VERSION
    request_id: str | None = None
    decision: Decision
    matched_rules: list[RuleMatch] = Field(default_factory=list)
    obligations: list[Obligation] = Field(default_factory=list)
    policy_bundle_id: str
    policy_bundle_hash: str
    classification: ClassifyResponse | None = None
    evaluated_at: datetime | None = None
