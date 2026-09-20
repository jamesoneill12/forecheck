from __future__ import annotations

from forecheck.contracts import ClassifyRequest, PolicyEvaluateRequest
from forecheck.integrations.local import LocalForecheck

from .conftest import make_context


def test_classify_returns_uncalibrated_scores() -> None:
    forecheck = LocalForecheck()
    response = forecheck.classify(ClassifyRequest(context=make_context()))
    assert response.scores
    assert all(not score.calibrated for score in response.scores)


def test_classify_and_evaluate_round_trip_uses_default_bundle() -> None:
    forecheck = LocalForecheck()
    decision = forecheck.classify_and_evaluate(make_context())
    assert decision.policy_bundle_id == "conservative"
    assert decision.classification is not None


def test_evaluate_accepts_context_only() -> None:
    forecheck = LocalForecheck()
    decision = forecheck.evaluate(PolicyEvaluateRequest(context=make_context()))
    assert decision.policy_bundle_id == "conservative"


def test_evaluate_accepts_precomputed_classification() -> None:
    forecheck = LocalForecheck()
    classification = forecheck.classify(ClassifyRequest(context=make_context()))
    decision = forecheck.evaluate(PolicyEvaluateRequest(classification=classification))
    assert decision.classification == classification


def test_bundle_override_changes_policy_bundle_id() -> None:
    forecheck = LocalForecheck(bundle="conservative")
    decision = forecheck.classify_and_evaluate(make_context(), bundle="permissive")
    assert decision.policy_bundle_id == "permissive"


def test_request_id_is_propagated() -> None:
    forecheck = LocalForecheck()
    decision = forecheck.classify_and_evaluate(make_context(), request_id="req-1")
    assert decision.request_id == "req-1"
