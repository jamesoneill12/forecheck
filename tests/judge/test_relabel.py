from __future__ import annotations

from datetime import UTC, datetime

from forecheck.contracts import LabelValue, RiskDimension
from forecheck.judge.relabel import relabel_with_judge
from forecheck.judge.schema import JudgeDimensionVerdict, JudgeLabelRow
from tests.evaluation.conftest import all_no_labels
from tests.judge.conftest import make_judge_example


def _judge_row(example_id: str, model: str = "judge-v1") -> JudgeLabelRow:
    labels = {d: JudgeDimensionVerdict(value=LabelValue.YES, rationale="r") for d in RiskDimension}
    return JudgeLabelRow(
        example_id=example_id,
        model=model,
        provider="openai_compat",
        strip_identity=False,
        labels=labels,
        parse_ok=True,
        retried=False,
        raw_completion="{}",
        input_tokens=1,
        output_tokens=1,
        created_at=datetime.now(UTC),
    )


def test_relabel_restricts_to_judged_example_ids() -> None:
    examples = [
        make_judge_example("ex-1", labels=all_no_labels()),
        make_judge_example("ex-2", labels=all_no_labels()),
        make_judge_example("ex-3", labels=all_no_labels()),
    ]
    judge_rows = [_judge_row("ex-1"), _judge_row("ex-3")]

    relabelled, labels_source = relabel_with_judge(examples, judge_rows)

    assert {e.example_id for e in relabelled} == {"ex-1", "ex-3"}
    assert "judge-v1" in labels_source


def test_relabel_replaces_generator_labels_with_judge_verdicts() -> None:
    examples = [make_judge_example("ex-1", labels=all_no_labels())]
    judge_rows = [_judge_row("ex-1")]

    relabelled, _ = relabel_with_judge(examples, judge_rows)

    values = relabelled[0].labels.values
    assert all(v == LabelValue.YES for v in values.values())
    assert relabelled[0].labels.derived_from == "llm_judge:judge-v1"


def test_relabel_marks_unparsed_dimensions_as_undetermined() -> None:
    examples = [make_judge_example("ex-1", labels=all_no_labels())]
    labels = dict.fromkeys(RiskDimension, None)
    labels[RiskDimension.FINANCIAL_COMMITMENT] = JudgeDimensionVerdict(
        value=LabelValue.YES, rationale="r"
    )
    judge_row = JudgeLabelRow(
        example_id="ex-1",
        model="judge-v1",
        provider="openai_compat",
        strip_identity=False,
        labels=labels,
        parse_ok=False,
        retried=True,
        raw_completion="broken",
        input_tokens=1,
        output_tokens=1,
        created_at=datetime.now(UTC),
    )

    relabelled, _ = relabel_with_judge(examples, [judge_row])

    values = relabelled[0].labels.values
    assert values[RiskDimension.FINANCIAL_COMMITMENT] == LabelValue.YES
    other = RiskDimension.EXTERNAL_COMMUNICATION
    assert values[other] == LabelValue.UNDETERMINED
