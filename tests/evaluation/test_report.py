from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from forecheck.contracts import RiskDimension
from forecheck.evaluation.metrics import DimensionMetrics, ThresholdMetrics
from forecheck.evaluation.report import DatasetIdentity, EvaluationClass, EvaluationReport

DIM = RiskDimension.FINANCIAL_COMMITMENT


def _dm(f1: float = 0.5) -> DimensionMetrics:
    return DimensionMetrics(
        dimension=DIM,
        n_evaluable=10,
        n_positive=5,
        positive_rate=0.5,
        auprc=0.6,
        auroc=0.7,
        brier=0.2,
        nll=0.5,
        ece=0.1,
        adaptive_ece=0.1,
        reliability_bins=(),
        at_threshold=ThresholdMetrics(threshold=0.5, precision=f1, recall=f1, f1=f1),
        at_optimal_threshold=None,
        optimal_threshold=None,
    )


def _minimal_report(evaluation_class: EvaluationClass) -> EvaluationReport:
    return EvaluationReport(
        evaluation_class=evaluation_class,
        dataset=DatasetIdentity(split=None, n=10, sha256=None),
        seed=0,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        dimensions={DIM: _dm()},
        macro={"f1": 0.5},
        worst_slice={"f1": ("some_slice", 0.4)},
    )


def test_evaluation_class_is_required() -> None:
    with pytest.raises(ValidationError):
        EvaluationReport.model_validate(
            {
                "dataset": {"split": None, "n": 10},
                "seed": 0,
                "created_at": datetime(2026, 1, 1, tzinfo=UTC),
                "dimensions": {},
                "macro": {},
                "worst_slice": {},
            }
        )


def test_markdown_shows_synthetic_disclaimer_for_synthetic_classes() -> None:
    report = _minimal_report(EvaluationClass.SYNTHETIC_IN_DISTRIBUTION)
    markdown = report._render_markdown()
    assert "Synthetic data. No real-world safety claim is made." in markdown
    assert "SYNTHETIC_IN_DISTRIBUTION" in markdown


def test_markdown_omits_disclaimer_for_external_or_human() -> None:
    report = _minimal_report(EvaluationClass.EXTERNAL_OR_HUMAN)
    markdown = report._render_markdown()
    assert "Synthetic data" not in markdown


def test_to_json_and_to_markdown_write_files(tmp_path: Path) -> None:
    report = _minimal_report(EvaluationClass.SYNTHETIC_HELDOUT_ADVERSARIAL)
    json_path = tmp_path / "report.json"
    md_path = tmp_path / "report.md"
    report.to_json(json_path)
    report.to_markdown(md_path)
    assert json_path.exists()
    assert md_path.exists()
    assert "synthetic_heldout_adversarial" in json_path.read_text()
    assert "SYNTHETIC_HELDOUT_ADVERSARIAL" in md_path.read_text()


def test_report_round_trips_through_json(tmp_path: Path) -> None:
    report = _minimal_report(EvaluationClass.SYNTHETIC_IN_DISTRIBUTION)
    path = tmp_path / "report.json"
    report.to_json(path)
    loaded = EvaluationReport.model_validate_json(path.read_text())
    assert loaded.evaluation_class is EvaluationClass.SYNTHETIC_IN_DISTRIBUTION
    assert loaded.dimensions[DIM].n_evaluable == 10
