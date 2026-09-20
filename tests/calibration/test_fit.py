from __future__ import annotations

import numpy as np

from forecheck.calibration.fit import fit_bundle
from forecheck.contracts import LABEL_SCHEMA_VERSION, CalibrationMethod, LabelValue, RiskDimension


def _make_split(
    n: int, seed: int, n_not_applicable: int = 0
) -> tuple[list[float], list[LabelValue]]:
    rng = np.random.default_rng(seed)
    true_logits = rng.normal(0.0, 2.0, size=n)
    probs = 1.0 / (1.0 + np.exp(-true_logits))
    raw_labels = rng.binomial(1, probs)
    labels: list[LabelValue] = [LabelValue.YES if v else LabelValue.NO for v in raw_labels]
    for i in range(n_not_applicable):
        labels[i] = LabelValue.NOT_APPLICABLE
    return list(true_logits), labels


def test_fit_bundle_produces_calibration_for_well_populated_dimension() -> None:
    scores, labels = _make_split(200, seed=0)
    report = fit_bundle(
        {RiskDimension.FINANCIAL_COMMITMENT: scores},
        {RiskDimension.FINANCIAL_COMMITMENT: labels},
        CalibrationMethod.TEMPERATURE,
        backend_model_id="mock-heuristic-v1",
        prompt_contract_hash="hash",
        dataset_sha256="sha",
    )
    dim = report.bundle.dimensions[RiskDimension.FINANCIAL_COMMITMENT]
    assert dim.degenerate is False
    assert dim.method is CalibrationMethod.TEMPERATURE
    assert dim.n_fit == 200
    assert "temperature" in dim.params
    assert report.bundle.label_schema_version == LABEL_SCHEMA_VERSION


def test_fit_bundle_skips_not_applicable_cells() -> None:
    scores, labels = _make_split(200, seed=1, n_not_applicable=50)
    report = fit_bundle(
        {RiskDimension.UNTRUSTED_DESTINATION: scores},
        {RiskDimension.UNTRUSTED_DESTINATION: labels},
        CalibrationMethod.VECTOR,
        backend_model_id="m",
        prompt_contract_hash="h",
        dataset_sha256="d",
    )
    dim = report.bundle.dimensions[RiskDimension.UNTRUSTED_DESTINATION]
    assert dim.n_fit == 150


def test_fit_bundle_marks_dimension_degenerate_below_min_positives() -> None:
    n = 100
    scores = list(np.random.default_rng(2).normal(size=n))
    labels = [LabelValue.NO] * (n - 3) + [LabelValue.YES] * 3
    report = fit_bundle(
        {RiskDimension.PRIVILEGE_ESCALATION: scores},
        {RiskDimension.PRIVILEGE_ESCALATION: labels},
        CalibrationMethod.TEMPERATURE,
        backend_model_id="m",
        prompt_contract_hash="h",
        dataset_sha256="d",
        min_positives=25,
    )
    dim = report.bundle.dimensions[RiskDimension.PRIVILEGE_ESCALATION]
    assert dim.degenerate is True
    assert dim.method is CalibrationMethod.NONE
    assert any("degenerate" in w for w in report.warnings)


def test_fit_bundle_marks_dimension_degenerate_with_single_class() -> None:
    n = 50
    scores = list(np.random.default_rng(3).normal(size=n))
    labels = [LabelValue.YES] * n
    report = fit_bundle(
        {RiskDimension.POLICY_CONFLICT: scores},
        {RiskDimension.POLICY_CONFLICT: labels},
        CalibrationMethod.TEMPERATURE,
        backend_model_id="m",
        prompt_contract_hash="h",
        dataset_sha256="d",
        min_positives=1,
    )
    dim = report.bundle.dimensions[RiskDimension.POLICY_CONFLICT]
    assert dim.degenerate is True


def test_fit_bundle_dimensions_not_supplied_are_absent() -> None:
    scores, labels = _make_split(200, seed=4)
    report = fit_bundle(
        {RiskDimension.FINANCIAL_COMMITMENT: scores},
        {RiskDimension.FINANCIAL_COMMITMENT: labels},
        CalibrationMethod.TEMPERATURE,
        backend_model_id="m",
        prompt_contract_hash="h",
        dataset_sha256="d",
    )
    assert RiskDimension.EXTERNAL_COMMUNICATION not in report.bundle.dimensions


def test_macro_ece_after_is_less_than_before_for_miscalibrated_scores() -> None:
    rng = np.random.default_rng(5)
    true_logits = rng.normal(0.0, 2.0, size=500)
    probs = 1.0 / (1.0 + np.exp(-true_logits))
    raw_labels = rng.binomial(1, probs)
    labels = [LabelValue.YES if v else LabelValue.NO for v in raw_labels]
    miscalibrated = list(true_logits * 4.0)

    report = fit_bundle(
        {RiskDimension.SENSITIVE_DATA_EXPOSURE: miscalibrated},
        {RiskDimension.SENSITIVE_DATA_EXPOSURE: labels},
        CalibrationMethod.TEMPERATURE,
        backend_model_id="m",
        prompt_contract_hash="h",
        dataset_sha256="d",
    )
    assert report.macro_ece_after < report.macro_ece_before
