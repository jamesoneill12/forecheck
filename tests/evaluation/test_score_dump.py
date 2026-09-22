from __future__ import annotations

import json
from pathlib import Path

from conftest import make_example

from forecheck.contracts import RiskDimension
from forecheck.contracts.io import TruncationInfo
from forecheck.evaluation.score_cache import write_score_dump
from forecheck.inference.base import RawScores


def test_write_score_dump_one_row_per_example(tmp_path: Path) -> None:
    examples = [make_example(example_id=f"ex-{i}") for i in range(3)]
    raw = [
        RawScores(scores=dict.fromkeys(RiskDimension, 0.5), truncation=TruncationInfo())
        for _ in examples
    ]
    probs = {d: [0.1, 0.2, 0.3] for d in RiskDimension}
    path = tmp_path / "scores.jsonl"
    write_score_dump(path, examples, raw, probs)
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert [r["example_id"] for r in rows] == [e.example_id for e in examples]
    assert rows[1]["probability"]["prompt_injection_influence"] == 0.2
    assert set(rows[0]["labels"]) == {d.value for d in RiskDimension}
