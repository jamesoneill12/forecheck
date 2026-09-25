from __future__ import annotations

from conftest import (
    StubBackend,
    StubPolicyEngine,
    all_no_labels,
    make_example,
    make_paraphrase_pair,
)

from forecheck.contracts import DifficultyTier, LabelValue, RiskDimension, Split
from forecheck.evaluation.report import EvaluationClass
from forecheck.evaluation.runner import evaluate


def _examples() -> list:
    easy = make_example("easy", difficulty=DifficultyTier.EASY, tool_name="email.send_message")
    hard = make_example(
        "hard",
        difficulty=DifficultyTier.HARD,
        tool_name="crypto.wire_transfer",
        labels=all_no_labels(**{RiskDimension.FINANCIAL_COMMITMENT: LabelValue.YES}),
    )
    base, transformed = make_paraphrase_pair(base_id="base", pair_id="pair-1", family_id="fam-2")
    return [easy, hard, base, transformed]


def test_evaluate_produces_report_with_required_evaluation_class() -> None:
    backend = StubBackend(default_score=0.3)
    report = evaluate(
        backend,
        _examples(),
        evaluation_class=EvaluationClass.SYNTHETIC_IN_DISTRIBUTION,
        n_boot=20,
    )
    assert report.evaluation_class is EvaluationClass.SYNTHETIC_IN_DISTRIBUTION
    assert report.dataset.n == 4
    assert set(report.dimensions.keys()) == set(RiskDimension)
    assert report.model is not None
    assert report.model.backend == "stub"


def test_evaluate_dimension_metrics_carry_bootstrap_ci() -> None:
    backend = StubBackend(
        scores_by_dimension={RiskDimension.FINANCIAL_COMMITMENT: 0.9}, default_score=0.1
    )
    examples = [
        make_example(
            f"e{i}",
            labels=all_no_labels(
                **{
                    RiskDimension.FINANCIAL_COMMITMENT: (
                        LabelValue.YES if i % 2 == 0 else LabelValue.NO
                    )
                }
            ),
        )
        for i in range(6)
    ]
    report = evaluate(
        backend, examples, evaluation_class=EvaluationClass.SYNTHETIC_IN_DISTRIBUTION, n_boot=30
    )
    dm = report.dimensions[RiskDimension.FINANCIAL_COMMITMENT]
    assert dm.ci is not None
    assert "f1" in dm.ci
    assert dm.ci["f1"].seed == report.seed


def test_evaluate_builds_slices_and_worst_slice() -> None:
    backend = StubBackend(default_score=0.5)
    report = evaluate(
        backend, _examples(), evaluation_class=EvaluationClass.SYNTHETIC_IN_DISTRIBUTION, n_boot=10
    )
    assert any(s.name.startswith("difficulty=") for s in report.slices)
    assert "f1" in report.worst_slice


def test_evaluate_computes_consistency_metrics() -> None:
    backend = StubBackend(default_score=0.4)
    report = evaluate(
        backend, _examples(), evaluation_class=EvaluationClass.SYNTHETIC_IN_DISTRIBUTION, n_boot=10
    )
    assert report.consistency is not None
    assert report.consistency.invariance.n_pairs == 1


def test_evaluate_computes_selective_metrics() -> None:
    backend = StubBackend(default_score=0.5)
    report = evaluate(
        backend, _examples(), evaluation_class=EvaluationClass.SYNTHETIC_IN_DISTRIBUTION, n_boot=10
    )
    assert report.selective is not None
    assert set(report.selective.keys()) == set(RiskDimension)


def test_evaluate_with_engine_populates_decisions() -> None:
    backend = StubBackend(default_score=0.95)
    engine = StubPolicyEngine(deny_threshold=0.5)
    report = evaluate(
        backend,
        _examples(),
        evaluation_class=EvaluationClass.SYNTHETIC_IN_DISTRIBUTION,
        engine=engine,
        n_boot=10,
    )
    assert report.decisions is not None
    assert report.decisions.n == 4


def test_evaluate_without_engine_has_no_decisions() -> None:
    backend = StubBackend(default_score=0.5)
    report = evaluate(
        backend, _examples(), evaluation_class=EvaluationClass.SYNTHETIC_IN_DISTRIBUTION, n_boot=10
    )
    assert report.decisions is None


def test_evaluate_with_stacking_synthetic_populates_stacking_report() -> None:
    backend = StubBackend(default_score=0.95)
    report = evaluate(
        backend,
        _examples(),
        evaluation_class=EvaluationClass.SYNTHETIC_IN_DISTRIBUTION,
        n_boot=10,
        stacking_synthetic=True,
    )
    assert report.stacking is not None
    ks = {row.k for row in report.stacking.rows}
    assert ks == set(range(1, 12))
    strategies = {row.strategy for row in report.stacking.rows}
    assert strategies == {"independent", "joint", "expected_cost_joint"}


def test_evaluate_without_stacking_flags_has_no_stacking_report() -> None:
    backend = StubBackend(default_score=0.5)
    report = evaluate(
        backend, _examples(), evaluation_class=EvaluationClass.SYNTHETIC_IN_DISTRIBUTION, n_boot=10
    )
    assert report.stacking is None


def test_evaluate_with_include_latency() -> None:
    backend = StubBackend(default_score=0.5)
    report = evaluate(
        backend,
        _examples(),
        evaluation_class=EvaluationClass.SYNTHETIC_IN_DISTRIBUTION,
        include_latency=True,
        n_boot=5,
    )
    assert report.latency is not None
    assert report.latency.overall.n == 4


def test_evaluate_with_training_tool_names_adds_out_of_domain_slice() -> None:
    backend = StubBackend(default_score=0.5)
    report = evaluate(
        backend,
        _examples(),
        evaluation_class=EvaluationClass.SYNTHETIC_IN_DISTRIBUTION,
        n_boot=5,
        training_tool_names=frozenset({"email.send_message"}),
    )
    assert any(s.name == "out_of_domain_tool" for s in report.slices)


def test_evaluate_with_threshold_selection_examples_sets_optimal_threshold() -> None:
    backend = StubBackend(
        scores_by_dimension={RiskDimension.FINANCIAL_COMMITMENT: 0.9}, default_score=0.1
    )
    eval_examples = [
        make_example(
            f"e{i}",
            labels=all_no_labels(
                **{
                    RiskDimension.FINANCIAL_COMMITMENT: (
                        LabelValue.YES if i % 2 == 0 else LabelValue.NO
                    )
                }
            ),
        )
        for i in range(4)
    ]
    selection_examples = [
        make_example(
            f"sel{i}",
            labels=all_no_labels(
                **{
                    RiskDimension.FINANCIAL_COMMITMENT: (
                        LabelValue.YES if i % 2 == 0 else LabelValue.NO
                    )
                }
            ),
            split=Split.DEV,
        )
        for i in range(4)
    ]
    report = evaluate(
        backend,
        eval_examples,
        evaluation_class=EvaluationClass.SYNTHETIC_IN_DISTRIBUTION,
        threshold_selection_examples=selection_examples,
        n_boot=5,
    )
    dm = report.dimensions[RiskDimension.FINANCIAL_COMMITMENT]
    assert dm.optimal_threshold is not None
    assert report.threshold_selection_split is Split.DEV
    assert report.macro["f1@selected"] is not None


def test_evaluate_without_threshold_selection_examples_leaves_selected_metrics_na() -> None:
    backend = StubBackend(default_score=0.5)
    report = evaluate(
        backend, _examples(), evaluation_class=EvaluationClass.SYNTHETIC_IN_DISTRIBUTION, n_boot=5
    )
    assert report.threshold_selection_split is None
    assert report.macro["f1@selected"] is None
    for dm in report.dimensions.values():
        assert dm.at_optimal_threshold is None
        assert dm.optimal_threshold is None


def test_evaluate_respects_explicit_dimensions_subset() -> None:
    backend = StubBackend(default_score=0.5)
    report = evaluate(
        backend,
        _examples(),
        evaluation_class=EvaluationClass.SYNTHETIC_IN_DISTRIBUTION,
        dimensions=[RiskDimension.FINANCIAL_COMMITMENT],
        n_boot=5,
    )
    assert set(report.dimensions.keys()) == {RiskDimension.FINANCIAL_COMMITMENT}


def test_probability_matrix_sigmoids_margins_for_uncalibrated_dimension() -> None:
    from forecheck.evaluation.runner import _apply_calibration

    values = [-10.0, 0.0, 10.0, None]
    passthrough = _apply_calibration(values, None)
    assert passthrough == values
    squashed = _apply_calibration(values, None, sigmoid_fallback=True)
    assert squashed[3] is None
    assert all(0.0 <= v <= 1.0 for v in squashed[:3] if v is not None)
    assert squashed[1] == 0.5
