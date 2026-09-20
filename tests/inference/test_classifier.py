from __future__ import annotations

from datetime import UTC, datetime

import pytest

from forecheck.calibration.base import CalibratorBundle, DimensionCalibration
from forecheck.calibration.methods import TemperatureScaling
from forecheck.contracts import (
    CalibrationMethod,
    ClassifyOptions,
    ClassifyRequest,
    RiskDimension,
)
from forecheck.inference.classifier import AbstainPolicy, Classifier
from forecheck.inference.mock import MockBackend
from forecheck.inference.prompt import prompt_contract_hash
from tests.inference.conftest import make_context


def _bundle(backend: MockBackend, **dim_overrides: DimensionCalibration) -> CalibratorBundle:
    dimensions = {}
    for dimension in RiskDimension:
        if dimension in dim_overrides:
            dimensions[dimension] = dim_overrides[dimension]
            continue
        calibrator = TemperatureScaling(temperature=1.0)
        dimensions[dimension] = DimensionCalibration(
            dimension=dimension,
            method=CalibrationMethod.TEMPERATURE,
            params=calibrator.to_params(),
            n_fit=100,
            n_positive=40,
            ece_after=0.05,
        )
    return CalibratorBundle(
        artifact_id="bundle-1",
        backend_model_id=backend.model_info.model_id,
        prompt_contract_hash=prompt_contract_hash(),
        label_schema_version="1.0",
        split_name="calibration",
        dataset_sha256="deadbeef",
        fitted_at=datetime.now(UTC),
        forecheck_version="0.1.0",
        dimensions=dimensions,
    )


def test_without_bundle_no_dimension_is_calibrated_or_has_probability() -> None:
    backend = MockBackend(seed=0)
    classifier = Classifier(backend)
    request = ClassifyRequest(context=make_context())
    response = classifier.classify(request)

    assert response.calibration.method == CalibrationMethod.NONE
    for score in response.scores:
        assert score.calibrated is False
        assert score.probability is None
        assert score.raw_score is None


def test_without_bundle_raw_score_only_returned_when_requested() -> None:
    backend = MockBackend(seed=0)
    classifier = Classifier(backend)
    request = ClassifyRequest(
        context=make_context(), options=ClassifyOptions(include_uncalibrated=True)
    )
    response = classifier.classify(request)
    for score in response.scores:
        assert score.raw_score is not None
        assert score.probability is None
        assert score.calibrated is False


def test_with_bundle_scores_are_calibrated_probabilities() -> None:
    backend = MockBackend(seed=0)
    bundle = _bundle(backend)
    classifier = Classifier(backend, bundle)
    response = classifier.classify(ClassifyRequest(context=make_context()))

    assert response.calibration.method == CalibrationMethod.TEMPERATURE
    for score in response.scores:
        if not score.abstained:
            assert score.calibrated is True
            assert score.probability is not None
            assert 0.0 <= score.probability <= 1.0


def test_bundle_prompt_contract_hash_mismatch_raises() -> None:
    backend = MockBackend(seed=0)
    bundle = _bundle(backend)
    bad_bundle = bundle.model_copy(update={"prompt_contract_hash": "not-the-real-hash"})
    with pytest.raises(ValueError, match="prompt_contract_hash"):
        Classifier(backend, bad_bundle)


def test_bundle_backend_model_id_mismatch_raises() -> None:
    backend = MockBackend(seed=0)
    bundle = _bundle(backend)
    bad_bundle = bundle.model_copy(update={"backend_model_id": "some-other-model"})
    with pytest.raises(ValueError, match="backend_model_id"):
        Classifier(backend, bad_bundle)


def test_degenerate_dimension_abstains() -> None:
    backend = MockBackend(seed=0)
    degenerate = DimensionCalibration(
        dimension=RiskDimension.POLICY_CONFLICT,
        method=CalibrationMethod.NONE,
        params={},
        n_fit=3,
        n_positive=1,
        degenerate=True,
    )
    bundle = _bundle(backend, **{RiskDimension.POLICY_CONFLICT: degenerate})
    classifier = Classifier(backend, bundle)
    response = classifier.classify(ClassifyRequest(context=make_context()))
    policy_score = response.by_dimension()[RiskDimension.POLICY_CONFLICT]
    assert policy_score.abstained is True
    assert policy_score.probability is None


def test_wide_interval_triggers_abstention() -> None:
    backend = MockBackend(seed=0)
    wide = DimensionCalibration(
        dimension=RiskDimension.POLICY_CONFLICT,
        method=CalibrationMethod.TEMPERATURE,
        params=TemperatureScaling(temperature=1.0).to_params(),
        n_fit=100,
        n_positive=40,
        ece_after=0.9,
    )
    bundle = _bundle(backend, **{RiskDimension.POLICY_CONFLICT: wide})
    classifier = Classifier(backend, bundle, abstain_policy=AbstainPolicy(max_interval_width=0.3))
    response = classifier.classify(ClassifyRequest(context=make_context()))
    policy_score = response.by_dimension()[RiskDimension.POLICY_CONFLICT]
    assert policy_score.abstained is True


def test_insufficient_context_drives_response_level_abstention() -> None:
    backend = MockBackend(seed=0)
    bundle = _bundle(backend)
    classifier = Classifier(
        backend, bundle, abstain_policy=AbstainPolicy(insufficient_context_threshold=0.01)
    )
    response = classifier.classify(ClassifyRequest(context=make_context()))
    assert response.abstained is True


def test_model_info_carries_prompt_contract_hash() -> None:
    backend = MockBackend(seed=0)
    classifier = Classifier(backend)
    response = classifier.classify(ClassifyRequest(context=make_context()))
    assert response.model.prompt_contract_hash == prompt_contract_hash()


def test_latency_is_measured_and_nonnegative() -> None:
    backend = MockBackend(seed=0)
    classifier = Classifier(backend)
    response = classifier.classify(ClassifyRequest(context=make_context()))
    assert response.latency_ms >= 0.0


def test_dimension_subset_is_respected() -> None:
    backend = MockBackend(seed=0)
    classifier = Classifier(backend)
    request = ClassifyRequest(
        context=make_context(),
        options=ClassifyOptions(dimensions=[RiskDimension.FINANCIAL_COMMITMENT]),
    )
    response = classifier.classify(request)
    assert {s.dimension for s in response.scores} == {RiskDimension.FINANCIAL_COMMITMENT}
