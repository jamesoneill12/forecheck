"""Judge-vs-generator agreement: per-dimension Cohen's kappa, agreement %, confusion
counts, and a disagreement dump for manual review.

Comparisons are computed only over the ``(dimension, example)`` cells where the
generator label is ``yes``/``no``/``not_applicable`` (never ``undetermined``, which the
generator never produces) and the judge's completion parsed successfully; rows where
the judge's completion never parsed are counted as ``n_unparseable`` and excluded from
both the confusion matrix's kappa/agreement inputs and the disagreement dump, since
there is no judge label to disagree with.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict
from sklearn.metrics import cohen_kappa_score

from forecheck.contracts import LabelValue, RiskDimension
from forecheck.judge.schema import JudgeLabelRow, JudgeSampleRow

__all__ = [
    "AgreementReport",
    "DimensionAgreement",
    "Disagreement",
    "compute_agreement",
    "find_disagreements",
    "render_agreement_markdown",
    "write_agreement_report",
]

_CATEGORIES: tuple[LabelValue, ...] = (
    LabelValue.YES,
    LabelValue.NO,
    LabelValue.NOT_APPLICABLE,
)
_CONFUSION_COLUMNS: tuple[str, ...] = (*[c.value for c in _CATEGORIES], "unparseable")


class DimensionAgreement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    dimension: RiskDimension
    n_compared: int
    n_unparseable: int
    agreement_rate: float | None
    cohen_kappa: float | None
    confusion: dict[str, dict[str, int]]


class AgreementReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model: str
    n_examples: int
    dimensions: dict[RiskDimension, DimensionAgreement]


class Disagreement(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    example_id: str
    dimension: RiskDimension
    generator_label: LabelValue
    judge_label: LabelValue
    judge_rationale: str


def _empty_confusion() -> dict[str, dict[str, int]]:
    return {c.value: dict.fromkeys(_CONFUSION_COLUMNS, 0) for c in _CATEGORIES}


def _kappa(gen_values: list[int], judge_values: list[int]) -> float | None:
    if not gen_values:
        return None
    raw = cohen_kappa_score(gen_values, judge_values, labels=list(range(len(_CATEGORIES))))
    return None if np.isnan(raw) else float(raw)


def compute_agreement(
    samples: Sequence[JudgeSampleRow], labels: Sequence[JudgeLabelRow]
) -> AgreementReport:
    labels_by_id = {row.example_id: row for row in labels}
    model_names = sorted({row.model for row in labels})
    model = model_names[0] if len(model_names) == 1 else "|".join(model_names)

    dimension_reports: dict[RiskDimension, DimensionAgreement] = {}
    for dimension in RiskDimension:
        confusion = _empty_confusion()
        gen_values: list[int] = []
        judge_values: list[int] = []
        n_unparseable = 0
        for sample in samples:
            judge_row = labels_by_id.get(sample.example_id)
            if judge_row is None:
                continue
            gen_label = sample.generator_labels.get(dimension)
            if gen_label not in _CATEGORIES:
                continue
            verdict = judge_row.labels.get(dimension)
            if verdict is None:
                n_unparseable += 1
                confusion[gen_label.value]["unparseable"] += 1
                continue
            confusion[gen_label.value][verdict.value.value] += 1
            gen_values.append(_CATEGORIES.index(gen_label))
            judge_values.append(_CATEGORIES.index(verdict.value))
        n_compared = len(gen_values)
        agreement_rate = (
            sum(1 for g, j in zip(gen_values, judge_values, strict=True) if g == j) / n_compared
            if n_compared
            else None
        )
        dimension_reports[dimension] = DimensionAgreement(
            dimension=dimension,
            n_compared=n_compared,
            n_unparseable=n_unparseable,
            agreement_rate=agreement_rate,
            cohen_kappa=_kappa(gen_values, judge_values),
            confusion=confusion,
        )
    return AgreementReport(model=model, n_examples=len(samples), dimensions=dimension_reports)


def find_disagreements(
    samples: Sequence[JudgeSampleRow], labels: Sequence[JudgeLabelRow]
) -> list[Disagreement]:
    labels_by_id = {row.example_id: row for row in labels}
    out: list[Disagreement] = []
    for sample in samples:
        judge_row = labels_by_id.get(sample.example_id)
        if judge_row is None:
            continue
        for dimension in RiskDimension:
            gen_label = sample.generator_labels.get(dimension)
            if gen_label not in _CATEGORIES:
                continue
            verdict = judge_row.labels.get(dimension)
            if verdict is None or verdict.value == gen_label:
                continue
            out.append(
                Disagreement(
                    example_id=sample.example_id,
                    dimension=dimension,
                    generator_label=gen_label,
                    judge_label=verdict.value,
                    judge_rationale=verdict.rationale,
                )
            )
    return out


def _fmt(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.4f}"


def render_agreement_markdown(report: AgreementReport) -> str:
    lines = [
        f"# forecheck LLM-judge agreement — {report.model}",
        "",
        f"n_examples={report.n_examples}",
        "",
        "| dimension | n_compared | n_unparseable | agreement | kappa |",
        "|---|---|---|---|---|",
    ]
    for dimension, dm in report.dimensions.items():
        lines.append(
            f"| {dimension.value} | {dm.n_compared} | {dm.n_unparseable} | "
            f"{_fmt(dm.agreement_rate)} | {_fmt(dm.cohen_kappa)} |"
        )
    lines.append("")
    lines.append("## Confusion (generator row vs judge column)")
    for dimension, dm in report.dimensions.items():
        lines.append("")
        lines.append(f"### {dimension.value}")
        lines.append("| generator \\ judge | " + " | ".join(_CONFUSION_COLUMNS) + " |")
        lines.append("|---" * (len(_CONFUSION_COLUMNS) + 1) + "|")
        for category in _CATEGORIES:
            row = dm.confusion[category.value]
            counts = " | ".join(str(row[c]) for c in _CONFUSION_COLUMNS)
            lines.append(f"| {category.value} | {counts} |")
    return "\n".join(lines) + "\n"


def write_agreement_report(
    out_dir: Path,
    report: AgreementReport,
    disagreements: Sequence[Disagreement],
) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "agreement.json").write_text(report.model_dump_json(indent=2), encoding="utf-8")
    (out_dir / "agreement.md").write_text(render_agreement_markdown(report), encoding="utf-8")
    with (out_dir / "disagreements.jsonl").open("w", encoding="utf-8") as handle:
        for row in disagreements:
            handle.write(row.model_dump_json())
            handle.write("\n")
