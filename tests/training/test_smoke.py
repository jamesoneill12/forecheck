from __future__ import annotations

from forecheck.contracts import LabelValue, RiskDimension, Split
from forecheck.training.smoke import build_synthetic_examples
from forecheck.training.smoke import test_smoke_cpu_train as test_smoke_cpu_train

__all__ = ["test_smoke_cpu_train"]


def test_build_synthetic_examples_are_valid_and_distinct() -> None:
    examples = build_synthetic_examples(6)

    assert len({e.example_id for e in examples}) == 6
    assert len({e.family_id for e in examples}) == 6
    for example in examples:
        assert example.split is Split.TRAIN
        assert set(example.labels.values) == set(RiskDimension)


def test_build_synthetic_examples_include_both_benign_and_risky_rows() -> None:
    examples = build_synthetic_examples(4)

    destructive = RiskDimension.DESTRUCTIVE_OR_IRREVERSIBLE_ACTION
    labels = {e.labels.values[destructive] for e in examples}

    assert LabelValue.YES in labels
    assert LabelValue.NO in labels
