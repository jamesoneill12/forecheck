"""Independent LLM-judge labelling of a stratified eval sample.

See ``docs/evaluation/llm-judge-labels.md`` for the motivation and how to run the
``forecheck judge sample|label|agreement`` pipeline end to end.
"""

from __future__ import annotations

from forecheck.judge.agreement import (
    AgreementReport,
    DimensionAgreement,
    Disagreement,
    compute_agreement,
    find_disagreements,
    write_agreement_report,
)
from forecheck.judge.labeling import (
    LabelRunResult,
    label_examples,
    load_label_cache,
    write_label_rows,
)
from forecheck.judge.relabel import relabel_with_judge
from forecheck.judge.sampling import SampleResult, render_coverage_table, stratified_sample
from forecheck.judge.schema import (
    JudgeDimensionVerdict,
    JudgeLabelRow,
    JudgeSampleRow,
    read_sample_rows,
    write_sample_rows,
)

__all__ = [
    "AgreementReport",
    "DimensionAgreement",
    "Disagreement",
    "JudgeDimensionVerdict",
    "JudgeLabelRow",
    "JudgeSampleRow",
    "LabelRunResult",
    "SampleResult",
    "compute_agreement",
    "find_disagreements",
    "label_examples",
    "load_label_cache",
    "read_sample_rows",
    "relabel_with_judge",
    "render_coverage_table",
    "stratified_sample",
    "write_agreement_report",
    "write_label_rows",
    "write_sample_rows",
]
