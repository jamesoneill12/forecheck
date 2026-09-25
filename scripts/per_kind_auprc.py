"""Per-withheld-kind AUPRC on ``heldout_policy_kind``.

Usage: per_kind_auprc.py [--withheld k1,k2] <heldout_policy_kind.jsonl> NAME=<scores.jsonl> [...]

Joins each checker's ``--dump-scores`` output to the split's latent policy predicates
and reports, for ``policy_conflict``, AUPRC and AUROC per withheld kind (rows whose
policies include that kind) plus the rows that carry no withheld kind at all. The
withheld set comes from ``--withheld``, else the manifest next to the data file, else
the repository default. Pre-ADR-0011 datasets (v4) need ``--withheld`` because the
enum has grown since and the hash-ranked default no longer reproduces their set.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

from sklearn.metrics import average_precision_score, roc_auc_score

from forecheck.data.splitting import HELDOUT_POLICY_KINDS

DIM = "policy_conflict"


def _withheld_kinds(data_path: Path, override: str | None) -> set[str]:
    if override:
        return set(override.split(","))
    manifest = data_path.with_suffix(".manifest.json")
    if manifest.exists():
        kinds = json.loads(manifest.read_text()).get("heldout_policy_kinds")
        if kinds:
            return set(kinds)
    return {k.value for k in HELDOUT_POLICY_KINDS}


def _load_kinds(data_path: Path) -> dict[str, set[str]]:
    kinds: dict[str, set[str]] = {}
    with data_path.open() as f:
        for line in f:
            row = json.loads(line)
            preds = row["latent"].get("policy_predicates") or []
            kinds[row["example_id"]] = {p["kind"] for p in preds}
    return kinds


def _load_scores(path: Path) -> dict[str, tuple[int, float]]:
    out: dict[str, tuple[int, float]] = {}
    with path.open() as f:
        for line in f:
            row = json.loads(line)
            label = row["labels"].get(DIM)
            if label not in ("yes", "no"):
                continue
            out[row["example_id"]] = (int(label == "yes"), float(row["raw"][DIM]))
    return out


def _metrics(pairs: list[tuple[int, float]]) -> str:
    y = [p[0] for p in pairs]
    s = [p[1] for p in pairs]
    n, pos = len(y), sum(y)
    if pos in (0, n):
        return f"n/a (n={n}, pos={pos})"
    return (
        f"{average_precision_score(y, s):.3f} / {roc_auc_score(y, s):.3f} "
        f"(n={n}, pos={pos / n:.2f})"
    )


def main(argv: list[str]) -> int:
    override = None
    if argv and argv[0] == "--withheld":
        override, argv = argv[1], argv[2:]
    if len(argv) < 2:
        print(__doc__, file=sys.stderr)
        return 2
    data_path = Path(argv[0])
    kinds = _load_kinds(data_path)
    withheld = _withheld_kinds(data_path, override)
    checkers = {a.split("=", 1)[0]: _load_scores(Path(a.split("=", 1)[1])) for a in argv[1:]}

    groups: dict[str, list[str]] = defaultdict(list)
    for eid, ks in kinds.items():
        hit = ks & withheld
        for k in hit:
            groups[k].append(eid)
        if not hit:
            groups["(no withheld kind)"].append(eid)

    print(f"withheld kinds: {sorted(withheld)}")
    print(f"rows: {len(kinds)}; checkers: {', '.join(checkers)}\n")
    print("| group | " + " | ".join(checkers) + " |")
    print("|---|" + "---|" * len(checkers))
    order = sorted(withheld) + ["(no withheld kind)", "(all rows)"]
    groups["(all rows)"] = list(kinds)
    for g in order:
        eids = groups.get(g, [])
        cells = []
        for scores in checkers.values():
            pairs = [scores[e] for e in eids if e in scores]
            cells.append(_metrics(pairs) if pairs else "n/a")
        print(f"| {g} | " + " | ".join(cells) + " |")
    print("\nCells: AUPRC / AUROC on policy_conflict raw margin.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
