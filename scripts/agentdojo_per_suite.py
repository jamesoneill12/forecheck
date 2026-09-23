"""Per-suite AUPRC/AUROC from `--dump-scores` dumps on the four-suite AgentDojo export.

Usage: python scripts/agentdojo_per_suite.py <agentdojo.jsonl> NAME=dump.jsonl [NAME=dump.jsonl ...]
"""

from __future__ import annotations

import collections
import json
import sys
from pathlib import Path

from sklearn.metrics import average_precision_score, roc_auc_score

DIMS = (
    "prompt_injection_influence",
    "unauthorized_scope",
    "policy_conflict",
    "financial_commitment",
    "destructive_or_irreversible_action",
)
SUITES = ("banking", "slack", "travel", "workspace")


def _suite_index(path: Path) -> dict[str, str]:
    index: dict[str, str] = {}
    with path.open() as handle:
        for line in handle:
            row = json.loads(line)
            index[row["example_id"]] = row["latent"]["family_id"].split(":")[1]
    return index


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    suites = _suite_index(Path(argv[0]))
    print("| arm | suite | " + " | ".join(DIMS) + " |")
    print("|---|---|" + "---|" * len(DIMS))
    for spec in argv[1:]:
        name, _, dump = spec.partition("=")
        by_suite: dict[str, list[dict]] = collections.defaultdict(list)
        with Path(dump).open() as handle:
            for line in handle:
                row = json.loads(line)
                by_suite[suites[row["example_id"]]].append(row)
        for suite in SUITES:
            cells = []
            for dim in DIMS:
                y = []
                p = []
                for row in by_suite[suite]:
                    label = row["labels"][dim]
                    score = row["raw"].get(dim)
                    if label in ("yes", "no") and score is not None:
                        y.append(1 if label == "yes" else 0)
                        p.append(score)
                if len(set(y)) < 2:
                    cells.append("--")
                    continue
                rate = sum(y) / len(y)
                cells.append(
                    f"{average_precision_score(y, p):.3f} / {roc_auc_score(y, p):.3f} ({rate:.3f})"
                )
            print(f"| {name} | {suite} | " + " | ".join(cells) + " |")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
