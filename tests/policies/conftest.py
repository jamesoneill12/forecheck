"""Shared factories for building minimal, valid contract objects in policy tests."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pytest

from forecheck.contracts import (
    ActionContext,
    AffectedResource,
    AgentIdentity,
    CalibrationInfo,
    CalibrationMethod,
    ClassifyResponse,
    Destination,
    DestinationRelationship,
    DimensionScore,
    Environment,
    FinancialExposure,
    ModelInfo,
    Observation,
    OperationKind,
    Principal,
    PrincipalType,
    ProposedAction,
    ResourceKind,
    RiskDimension,
    Sensitivity,
    Stage,
    ToolFamily,
    TrajectoryStep,
    TrustLevel,
    UserObjective,
)

POLICIES_DIR = Path(__file__).resolve().parents[2] / "policies"


def make_model_info() -> ModelInfo:
    return ModelInfo(
        backend="test",
        model_id="test-risk-model",
        prompt_contract_hash="0" * 16,
        label_schema_version="1.0",
    )


def make_classification(
    scores: dict[RiskDimension, float] | None = None,
    *,
    abstained: Iterable[RiskDimension] = (),
    calibrated: bool = True,
    raw_scores: dict[RiskDimension, float] | None = None,
    request_id: str | None = None,
) -> ClassifyResponse:
    """Build a minimal :class:`ClassifyResponse` for the given probabilities.

    ``scores`` maps dimension to probability when ``calibrated`` is True. When
    ``calibrated`` is False, the same values are exposed only as ``raw_score``, with no
    ``probability``, matching what a real uncalibrated backend returns.
    """
    scores = dict(scores or {})
    raw_scores = dict(raw_scores or {})
    abstained_set = set(abstained)
    dimension_scores: list[DimensionScore] = []
    for dimension in set(scores) | abstained_set | set(raw_scores):
        if dimension in abstained_set:
            dimension_scores.append(DimensionScore(dimension=dimension, abstained=True))
            continue
        value = scores.get(dimension)
        raw_value = raw_scores.get(dimension, value)
        dimension_scores.append(
            DimensionScore(
                dimension=dimension,
                probability=value if calibrated else None,
                raw_score=raw_value,
                calibrated=calibrated and value is not None,
            )
        )
    return ClassifyResponse(
        request_id=request_id,
        scores=dimension_scores,
        model=make_model_info(),
        calibration=CalibrationInfo(
            method=CalibrationMethod.TEMPERATURE if calibrated else CalibrationMethod.NONE
        ),
        latency_ms=1.0,
    )


def make_context(
    *,
    objective: UserObjective | None = None,
    principal: Principal | None = None,
    agent: AgentIdentity | None = None,
    proposed_action: ProposedAction | None = None,
    environment: Environment | None = None,
    trajectory: list[TrajectoryStep] | None = None,
    observations: list[Observation] | None = None,
    resources: list[AffectedResource] | None = None,
    destination: Destination | None = None,
    financial: FinancialExposure | None = None,
) -> ActionContext:
    """Build a minimal, benign :class:`ActionContext`: an authorized human reading a
    file with no untrusted content, no destination, no financial exposure."""
    return ActionContext(
        objective=objective
        or UserObjective(text="Read the quarterly report.", authorization_explicit=True),
        principal=principal or Principal(id="user-1", type=PrincipalType.HUMAN, mfa_satisfied=True),
        agent=agent or AgentIdentity(id="agent-1", delegated_scopes=["*"]),
        proposed_action=proposed_action
        or ProposedAction(tool_name="read_document", tool_family=ToolFamily.FILE_STORAGE),
        environment=environment or Environment(),
        trajectory=trajectory or [],
        observations=observations or [],
        resources=resources or [],
        destination=destination,
        financial=financial,
    )


def benign_classification(
    scores: dict[RiskDimension, float] | None = None, **kwargs: object
) -> ClassifyResponse:
    """All eleven dimensions scored at 0.0 (known, not abstained), with overrides."""
    baseline = dict.fromkeys(RiskDimension, 0.0)
    baseline.update(scores or {})
    return make_classification(baseline, **kwargs)  # type: ignore[arg-type]


def benign_context(**overrides: object) -> ActionContext:
    """A fully known, unambiguous benign action: an authorized human, MFA satisfied,
    reading a public file in development, no untrusted content, a small authorized
    financial exposure, a same-tenant destination.

    Every fact the shipped bundles reference resolves to a real known value here, so a
    single-rule test can override just the fields that rule cares about without any
    other rule's ``fact`` leaf silently resolving to unknown.
    """
    defaults: dict[str, object] = {
        "objective": UserObjective(
            text="Read the public onboarding guide.", authorization_explicit=True
        ),
        "principal": Principal(id="user-1", type=PrincipalType.HUMAN, mfa_satisfied=True),
        "agent": AgentIdentity(id="agent-1", delegated_scopes=["*"]),
        "proposed_action": ProposedAction(
            tool_name="read_document", tool_family=ToolFamily.FILE_STORAGE
        ),
        "environment": Environment(stage=Stage.DEVELOPMENT, change_freeze=False),
        "resources": [
            AffectedResource(
                urn="urn:file:onboarding",
                kind=ResourceKind.FILE,
                sensitivity=Sensitivity.PUBLIC,
                operation=OperationKind.READ,
                reversible=True,
            )
        ],
        "destination": Destination(
            identifier="colleague@tenant.example",
            relationship=DestinationRelationship.SAME_TENANT,
            trust=TrustLevel.TRUSTED_TOOL,
            verified=True,
        ),
        "financial": FinancialExposure(amount=1.0, currency="USD"),
    }
    defaults.update(overrides)
    return make_context(**defaults)  # type: ignore[arg-type]


@pytest.fixture
def policies_dir() -> Path:
    return POLICIES_DIR
