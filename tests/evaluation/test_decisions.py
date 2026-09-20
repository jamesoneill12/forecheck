from __future__ import annotations

from conftest import StubPolicyEngine, all_no_labels, make_example

from forecheck.contracts import (
    CalibrationInfo,
    ClassifyResponse,
    DimensionScore,
    LabelValue,
    ModelInfo,
    RiskDimension,
    TruncationInfo,
)
from forecheck.evaluation.decisions import CostMatrix, decision_metrics

MODEL_INFO = ModelInfo(
    backend="stub", model_id="stub-v1", prompt_contract_hash="n/a", label_schema_version="1.0"
)
CALIBRATION_INFO = CalibrationInfo()


def _response(probabilities: dict[RiskDimension, float]) -> ClassifyResponse:
    scores = [
        DimensionScore(dimension=d, probability=p, calibrated=True)
        for d, p in probabilities.items()
    ]
    return ClassifyResponse(
        scores=scores,
        model=MODEL_INFO,
        calibration=CALIBRATION_INFO,
        truncation=TruncationInfo(),
        latency_ms=1.0,
    )


def test_false_allow_rate_counts_only_eligible_examples() -> None:
    dangerous = make_example(
        "dangerous",
        labels=all_no_labels(**{RiskDimension.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION: LabelValue.YES}),
    )
    benign = make_example("benign")
    engine = StubPolicyEngine(deny_threshold=0.99)
    responses = [
        _response({RiskDimension.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION: 0.1}),
        _response({RiskDimension.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION: 0.1}),
    ]
    result = decision_metrics(engine, responses, [dangerous, benign])
    assert result.false_allow_rate == 1.0
    assert result.n_allow == 2


def test_false_deny_rate_counts_only_benign_hard_negatives() -> None:
    benign_hard_negative = make_example("bhn", is_benign_hard_negative=True)
    ordinary = make_example("ordinary", is_benign_hard_negative=False)
    engine = StubPolicyEngine(deny_threshold=0.5)
    responses = [
        _response({RiskDimension.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION: 0.95}),
        _response({RiskDimension.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION: 0.95}),
    ]
    result = decision_metrics(engine, responses, [benign_hard_negative, ordinary])
    assert result.false_deny_rate == 1.0
    assert result.n_deny == 2


def test_no_eligible_examples_gives_none_rates() -> None:
    example = make_example("clean")
    engine = StubPolicyEngine()
    responses = [_response({RiskDimension.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION: 0.1})]
    result = decision_metrics(engine, responses, [example])
    assert result.false_allow_rate is None
    assert result.false_deny_rate is None


def test_risk_weighted_cost_uses_irreversible_weight() -> None:
    dangerous = make_example(
        "dangerous",
        labels=all_no_labels(**{RiskDimension.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION: LabelValue.YES}),
    )
    engine = StubPolicyEngine(deny_threshold=0.99)
    responses = [_response({RiskDimension.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION: 0.1})]
    cost_matrix = CostMatrix(false_allow_on_irreversible=42.0)
    result = decision_metrics(engine, responses, [dangerous], cost_matrix=cost_matrix)
    assert result.total_risk_weighted_cost == 42.0


def test_review_rate_and_cost() -> None:
    class _ReviewEngine:
        bundle_id = "review-bundle"
        bundle_hash = "hash"

        @property
        def default_decision(self) -> str:
            from forecheck.contracts import Decision

            return Decision.REVIEW

        def evaluate(self, classification: ClassifyResponse, context: object = None) -> object:
            from forecheck.contracts import Decision, PolicyDecision

            return PolicyDecision(
                decision=Decision.REVIEW,
                policy_bundle_id=self.bundle_id,
                policy_bundle_hash=self.bundle_hash,
            )

    example = make_example("e")
    responses = [_response({RiskDimension.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION: 0.5})]
    result = decision_metrics(_ReviewEngine(), responses, [example])
    assert result.review_rate == 1.0
    assert result.total_risk_weighted_cost == CostMatrix().review


def test_mismatched_lengths_raise() -> None:
    engine = StubPolicyEngine()
    example = make_example("e")
    import pytest

    with pytest.raises(ValueError, match="same length"):
        decision_metrics(engine, [], [example])
