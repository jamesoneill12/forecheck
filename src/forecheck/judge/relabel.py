"""Re-scores examples against LLM-judge verdicts instead of generator ground truth, for
``forecheck evaluate --labels-from``.
"""

from __future__ import annotations

from collections.abc import Sequence

from forecheck.contracts import Example, LabelSet, LabelValue, RiskDimension
from forecheck.judge.schema import JudgeLabelRow

__all__ = ["relabel_with_judge"]


def relabel_with_judge(
    examples: Sequence[Example], judge_rows: Sequence[JudgeLabelRow]
) -> tuple[list[Example], str]:
    """Restrict ``examples`` to those with a judge verdict, and replace their labels.

    A dimension the judge never parsed a verdict for becomes
    :attr:`~forecheck.contracts.LabelValue.UNDETERMINED`, so it is excluded from metrics
    the same way an abstained backend prediction is, rather than silently guessed at.
    Returns the relabelled examples and a ``labels_source`` string for the report header.
    """
    by_id = {row.example_id: row for row in judge_rows}
    models = sorted({row.model for row in judge_rows})
    labels_source = f"llm judge {'|'.join(models)}" if models else "llm judge"

    out: list[Example] = []
    for example in examples:
        judge_row = by_id.get(example.example_id)
        if judge_row is None:
            continue
        values: dict[RiskDimension, LabelValue] = {}
        for dimension in RiskDimension:
            verdict = judge_row.labels.get(dimension)
            values[dimension] = verdict.value if verdict is not None else LabelValue.UNDETERMINED
        new_labels = LabelSet(
            values=values,
            derivation_version=example.labels.derivation_version,
            derived_from=f"llm_judge:{judge_row.model}",
        )
        out.append(example.model_copy(update={"labels": new_labels}))
    return out, labels_source
