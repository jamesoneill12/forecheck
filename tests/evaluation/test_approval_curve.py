from __future__ import annotations

import random
from itertools import pairwise

import pytest
from conftest import all_no_labels, make_example

from forecheck.contracts import (
    CalibrationInfo,
    CalibrationMethod,
    ClassifyResponse,
    Decision,
    DimensionScore,
    LabelValue,
    ModelInfo,
    RiskDimension,
    TruncationInfo,
)
from forecheck.evaluation.approval_curve import (
    DEFAULT_BUDGETS,
    ApprovalElimination,
    IncidentRateMode,
    approval_elimination_curve,
)
from forecheck.policies.dsl import Condition, PolicyBundle, Rule, UnknownAs
from forecheck.policies.engine import DeterministicPolicyEngine

MODEL_INFO = ModelInfo(
    backend="stub", model_id="stub-v1", prompt_contract_hash="n/a", label_schema_version="1.0"
)
CALIBRATION_INFO = CalibrationInfo(method=CalibrationMethod.TEMPERATURE)
DIM = RiskDimension.FINANCIAL_COMMITMENT


def _response(p: float) -> ClassifyResponse:
    scores = [
        DimensionScore(dimension=d, probability=p if d is DIM else 0.0, calibrated=True)
        for d in RiskDimension
    ]
    return ClassifyResponse(
        scores=scores,
        model=MODEL_INFO,
        calibration=CALIBRATION_INFO,
        truncation=TruncationInfo(),
        latency_ms=1.0,
    )


def _bundle() -> PolicyBundle:
    rule = Rule(
        id="deny_high_financial",
        description="deny high financial commitment",
        decision=Decision.DENY,
        when=Condition(score=DIM, gte=0.5),
    )
    return PolicyBundle(
        bundle_id="single-dim",
        version=1,
        dsl_version="1.0",
        description="single-dimension guard",
        default_decision=Decision.ALLOW,
        uncalibrated_decision=Decision.REVIEW,
        allow_uncalibrated=True,
        unknown_as=UnknownAs.WORST_CASE,
        rules=[rule],
    )


def _engine() -> DeterministicPolicyEngine:
    return DeterministicPolicyEngine(_bundle(), "hash")


def _random_dataset(n: int, seed: int) -> tuple[list, list[ClassifyResponse]]:
    """``n`` examples whose score IS its true risk probability: label ~ Bernoulli(score).

    Sorting ascending by this score is therefore genuinely informative (unlike a score
    independent of the label), which is what makes the elimination-vs-budget scaling
    law in ``test_random_but_calibrated_score_scales_with_budget_over_base_rate``
    analytically tractable: for scores drawn ~ Uniform(0,1), sorting ascending and
    taking the prefix up to score threshold tau gives incident_rate(tau) = tau/2 and
    allow_fraction(tau) = tau, i.e. elimination(budget) ~= 2*budget = budget/base_rate
    since base_rate = E[score] = 0.5.
    """
    rng = random.Random(seed)
    examples = []
    responses = []
    for i in range(n):
        score = rng.random()
        risky = rng.random() < score
        examples.append(
            make_example(
                f"ex-{i}",
                family_id=f"fam-{i}",
                labels=all_no_labels(**{DIM: LabelValue.YES if risky else LabelValue.NO}),
            )
        )
        responses.append(_response(score))
    return examples, responses


def test_perfectly_separable_score_gives_full_elimination_at_every_budget() -> None:
    n = 2000
    examples = [make_example(f"benign-{i}", family_id=f"fam-{i}") for i in range(n - 1)]
    examples.append(
        make_example(
            "risky",
            family_id="fam-risky",
            labels=all_no_labels(**{DIM: LabelValue.YES}),
        )
    )
    responses = [_response(0.0) for _ in range(n - 1)] + [_response(1.0)]

    result = approval_elimination_curve(_engine(), responses, examples, budgets=DEFAULT_BUDGETS)

    assert result.base_incident_rate == 1 / n
    for point in result.operating_points:
        assert point.approvals_eliminated == 1.0
        assert point.review_fraction == 0.0
        assert point.deny_fraction == 0.0
        assert point.n_allow == n


def test_random_but_calibrated_score_scales_with_budget_over_base_rate() -> None:
    examples, responses = _random_dataset(20_000, seed=42)

    result = approval_elimination_curve(_engine(), responses, examples, budgets=DEFAULT_BUDGETS)
    base_rate = result.base_incident_rate
    assert base_rate is not None

    by_budget = {point.budget: point.approvals_eliminated for point in result.operating_points}
    # smallest budget allows too few examples for the ratio check to be stable
    assert by_budget[0.001] < 0.05
    for budget in (0.005, 0.01, 0.02, 0.05):
        expected = budget / base_rate
        ratio = by_budget[budget] / expected
        assert 0.15 <= ratio <= 2.0, (budget, by_budget[budget], expected)


def test_elimination_is_monotonic_in_budget() -> None:
    examples, responses = _random_dataset(500, seed=7)

    result = approval_elimination_curve(_engine(), responses, examples, budgets=DEFAULT_BUDGETS)

    fractions = [point.approvals_eliminated for point in result.operating_points]
    assert fractions == sorted(fractions)
    incident_rates = [
        point.incident_rate for point in result.operating_points if point.incident_rate is not None
    ]
    assert all(a <= b + 1e-12 for a, b in pairwise(incident_rates))


def test_serialisation_round_trip() -> None:
    examples, responses = _random_dataset(50, seed=3)

    result = approval_elimination_curve(_engine(), responses, examples, budgets=DEFAULT_BUDGETS)

    restored = ApprovalElimination.model_validate_json(result.model_dump_json())
    assert restored == result


def test_response_and_example_length_mismatch_raises() -> None:
    examples, responses = _random_dataset(3, seed=1)
    try:
        approval_elimination_curve(_engine(), responses[:2], examples)
    except ValueError as exc:
        assert "same length" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_reweight_to_target_base_rate_gives_effective_rate_and_total_weight() -> None:
    n = 20_000
    examples, responses = _random_dataset(n, seed=42)

    result = approval_elimination_curve(
        _engine(), responses, examples, budgets=DEFAULT_BUDGETS, target_base_rate=0.05
    )

    assert result.target_base_rate == 0.05
    assert result.effective_base_rate == pytest.approx(0.05, abs=1e-9)
    assert result.weights is not None
    assert len(result.weights) == n
    assert sum(result.weights) == pytest.approx(n, rel=1e-9)
    assert result.reweighted_operating_points is not None
    restored = ApprovalElimination.model_validate_json(result.model_dump_json())
    assert restored == result


def test_perfectly_separable_score_gives_full_elimination_under_both_modes() -> None:
    n = 20_000
    examples = [make_example(f"benign-{i}", family_id=f"fam-{i}") for i in range(n - 1)]
    examples.append(
        make_example(
            "risky",
            family_id="fam-risky",
            labels=all_no_labels(**{DIM: LabelValue.YES}),
        )
    )
    responses = [_response(0.0) for _ in range(n - 1)] + [_response(1.0)]

    for mode in (IncidentRateMode.PREFIX, IncidentRateMode.SMOOTHED):
        result = approval_elimination_curve(
            _engine(), responses, examples, budgets=DEFAULT_BUDGETS, incident_rate_mode=mode
        )
        for point in result.operating_points:
            assert point.approvals_eliminated == 1.0, mode
            assert point.review_fraction == 0.0, mode
            assert point.deny_fraction == 0.0, mode
            assert point.n_allow == n, mode


def test_smoothed_mode_monotone_and_never_exceeds_prefix_mode() -> None:
    examples, responses = _random_dataset(2_000, seed=11)
    budgets = (0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2)

    prefix_result = approval_elimination_curve(
        _engine(), responses, examples, budgets=budgets, incident_rate_mode=IncidentRateMode.PREFIX
    )
    smoothed_result = approval_elimination_curve(
        _engine(),
        responses,
        examples,
        budgets=budgets,
        incident_rate_mode=IncidentRateMode.SMOOTHED,
    )

    smoothed_fracs = [p.approvals_eliminated for p in smoothed_result.operating_points]
    prefix_fracs = [p.approvals_eliminated for p in prefix_result.operating_points]
    assert smoothed_fracs == sorted(smoothed_fracs)
    assert all(s <= p + 1e-12 for s, p in zip(smoothed_fracs, prefix_fracs, strict=True))
