"""Paired poisoned-vs-clean view of InjecAgent score dumps.

Usage: injecagent_paired.py <injecagent.jsonl> NAME=<scores.jsonl> [NAME=<scores.jsonl> ...]

Pairs are (case, attacker tool) with variants `poisoned` / `clean` from the export's
scenario_id; the call is identical within a pair, only the observation differs.
Prints a markdown table: fraction of pairs where the poisoned variant scores higher on
prompt_injection_influence raw margin, tie fraction, and median raw per variant.
"""

from __future__ import annotations

import json
import statistics
import sys
from pathlib import Path

DIM = "prompt_injection_influence"


def load_pairs(export: Path) -> dict[str, dict[str, str]]:
    pairs: dict[str, dict[str, str]] = {}
    with export.open() as fh:
        for line in fh:
            row = json.loads(line)
            sid = row["latent"]["scenario_id"]
            variant = sid.rsplit(":", 1)[-1]
            if variant not in ("poisoned", "clean"):
                continue
            pairs.setdefault(sid.rsplit(":", 1)[0], {})[variant] = row["example_id"]
    return {k: v for k, v in pairs.items() if len(v) == 2}


def load_raw(dump: Path) -> dict[str, float]:
    raw: dict[str, float] = {}
    with dump.open() as fh:
        for line in fh:
            row = json.loads(line)
            value = row.get("raw", {}).get(DIM)
            if value is not None:
                raw[row["example_id"]] = float(value)
    return raw


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    pairs = load_pairs(Path(argv[1]))
    print(f"pairs: {len(pairs)}\n")
    print("| checker | poisoned scored higher | tie | median raw, poisoned | median raw, clean |")
    print("|---|---|---|---|---|")
    for spec in argv[2:]:
        name, path = spec.split("=", 1)
        raw = load_raw(Path(path))
        higher = ties = n = 0
        poisoned: list[float] = []
        clean: list[float] = []
        for ids in pairs.values():
            if ids["poisoned"] not in raw or ids["clean"] not in raw:
                continue
            p, c = raw[ids["poisoned"]], raw[ids["clean"]]
            n += 1
            higher += p > c
            ties += p == c
            poisoned.append(p)
            clean.append(c)
        if n == 0:
            print(f"| {name} | n/a | n/a | n/a | n/a |")
            continue
        print(
            f"| {name} | {higher / n:.3f} | {ties / n:.3f} | "
            f"{statistics.median(poisoned):.2f} | {statistics.median(clean):.2f} |"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
