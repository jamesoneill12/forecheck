from __future__ import annotations

from datetime import UTC, datetime

import pytest

from forecheck.contracts import DifficultyTier, LabelValue, RiskDimension, Split
from forecheck.judge.agreement import compute_agreement, find_disagreements
from forecheck.judge.schema import JudgeDimensionVerdict, JudgeLabelRow, JudgeSampleRow

DIM = RiskDimension.FINANCIAL_COMMITMENT
OTHER_DIM = RiskDimension.EXTERNAL_COMMUNICATION


def _sample(example_id: str, dim_label: LabelValue) -> JudgeSampleRow:
    labels = dict.fromkeys(RiskDimension, LabelValue.NO)
    labels[DIM] = dim_label
    return JudgeSampleRow(
        example_id=example_id,
        family_id=f"{example_id}-fam",
        split=Split.TEST,
        tool_family=None,
        policy_kinds=(),
        difficulty=DifficultyTier.MEDIUM,
        rendered_full="full",
        rendered_stripped="stripped",
        generator_labels=labels,
    )


def _judge_row(
    example_id: str, dim_value: LabelValue | None, *, parse_ok: bool = True
) -> JudgeLabelRow:
    labels: dict[RiskDimension, JudgeDimensionVerdict | None] = dict.fromkeys(RiskDimension, None)
    for dimension in RiskDimension:
        if dimension == DIM:
            labels[dimension] = (
                JudgeDimensionVerdict(value=dim_value, rationale="r") if dim_value else None
            )
        else:
            labels[dimension] = JudgeDimensionVerdict(value=LabelValue.NO, rationale="r")
    return JudgeLabelRow(
        example_id=example_id,
        model="fake-judge-v1",
        provider="openai_compat",
        strip_identity=False,
        labels=labels,
        parse_ok=parse_ok,
        retried=False,
        raw_completion="{}",
        input_tokens=10,
        output_tokens=5,
        cost_usd=None,
        created_at=datetime.now(UTC),
    )


# po=0.8, pe=0.6*0.6+0.4*0.4=0.52, kappa=(0.8-0.52)/(1-0.52)=7/12.
_HAND_COMPUTED_ROWS: list[tuple[str, LabelValue, LabelValue]] = [
    ("ex-0", LabelValue.YES, LabelValue.YES),
    ("ex-1", LabelValue.YES, LabelValue.YES),
    ("ex-2", LabelValue.YES, LabelValue.YES),
    ("ex-3", LabelValue.YES, LabelValue.YES),
    ("ex-4", LabelValue.YES, LabelValue.YES),
    ("ex-5", LabelValue.YES, LabelValue.NO),
    ("ex-6", LabelValue.NO, LabelValue.YES),
    ("ex-7", LabelValue.NO, LabelValue.NO),
    ("ex-8", LabelValue.NO, LabelValue.NO),
    ("ex-9", LabelValue.NO, LabelValue.NO),
]


def test_cohen_kappa_matches_hand_computed_value() -> None:
    samples = [_sample(eid, gen) for eid, gen, _judge in _HAND_COMPUTED_ROWS]
    labels = [_judge_row(eid, judge) for eid, _gen, judge in _HAND_COMPUTED_ROWS]

    report = compute_agreement(samples, labels)
    dm = report.dimensions[DIM]

    assert dm.n_compared == 10
    assert dm.agreement_rate == pytest.approx(0.8)
    assert dm.cohen_kappa == pytest.approx(7 / 12)
    assert dm.confusion["yes"]["yes"] == 5
    assert dm.confusion["yes"]["no"] == 1
    assert dm.confusion["no"]["yes"] == 1
    assert dm.confusion["no"]["no"] == 3


def test_perfect_agreement_on_a_single_class_yields_undefined_kappa() -> None:
    rows = [(f"ex-{i}", LabelValue.NO, LabelValue.NO) for i in range(5)]
    samples = [_sample(eid, gen) for eid, gen, _judge in rows]
    labels = [_judge_row(eid, judge) for eid, _gen, judge in rows]

    report = compute_agreement(samples, labels)
    dm = report.dimensions[DIM]

    assert dm.agreement_rate == pytest.approx(1.0)
    assert dm.cohen_kappa is None


def test_not_applicable_is_its_own_confusion_category_not_a_negative() -> None:
    rows = [
        ("ex-0", LabelValue.NOT_APPLICABLE, LabelValue.NOT_APPLICABLE),
        ("ex-1", LabelValue.NOT_APPLICABLE, LabelValue.YES),
        ("ex-2", LabelValue.YES, LabelValue.NOT_APPLICABLE),
    ]
    samples = [_sample(eid, gen) for eid, gen, _judge in rows]
    labels = [_judge_row(eid, judge) for eid, _gen, judge in rows]

    report = compute_agreement(samples, labels)
    dm = report.dimensions[DIM]

    assert dm.n_compared == 3
    assert dm.confusion["not_applicable"]["not_applicable"] == 1
    assert dm.confusion["not_applicable"]["yes"] == 1
    assert dm.confusion["yes"]["not_applicable"] == 1


def test_unparseable_judge_output_is_excluded_from_kappa_and_counted_separately() -> None:
    rows = [("ex-0", LabelValue.YES, LabelValue.YES), ("ex-1", LabelValue.NO, LabelValue.NO)]
    samples = [_sample(eid, gen) for eid, gen, _judge in rows]
    labels = [_judge_row(eid, judge) for eid, _gen, judge in rows]
    labels.append(_judge_row("ex-2", None, parse_ok=False))
    samples.append(_sample("ex-2", LabelValue.YES))

    report = compute_agreement(samples, labels)
    dm = report.dimensions[DIM]

    assert dm.n_compared == 2
    assert dm.n_unparseable == 1
    assert dm.confusion["yes"]["unparseable"] == 1


def test_find_disagreements_only_reports_mismatched_evaluable_cells() -> None:
    samples = [_sample(eid, gen) for eid, gen, _judge in _HAND_COMPUTED_ROWS]
    labels = [_judge_row(eid, judge) for eid, _gen, judge in _HAND_COMPUTED_ROWS]

    disagreements = find_disagreements(samples, labels)

    assert {d.example_id for d in disagreements} == {"ex-5", "ex-6"}
    assert all(d.dimension == DIM for d in disagreements)
