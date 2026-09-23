"""Audit the InjecAgent poisoned/clean pairs and bootstrap the checker AUPRCs.

Usage: injecagent_pair_audit.py <injecagent.jsonl> NAME=<scores.jsonl> [...]

Reports, per checker: wins / ties / losses on prompt_injection_influence raw margin,
the tie-adjusted win rate (win + tie/2), a two-sided sign test on decided pairs, and
95% bootstrap CIs (over examples) for AUPRC on the three headline dimensions. Also
reports two construction facts about the pairs themselves: how often the poisoned
observation is longer than its clean twin, and how often the rendered destination
trust differs inside a pair.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import average_precision_score

DIMS = ("prompt_injection_influence", "unauthorized_scope", "policy_conflict")


def observation_chars(ctx: dict) -> int:
    total = 0
    for obs in ctx.get("observations") or []:
        total += len(json.dumps(obs, sort_keys=True))
    for step in ctx.get("trajectory") or []:
        total += len(json.dumps(step, sort_keys=True))
    return total


def load_export(path: Path):
    rows = {}
    pairs: dict[str, dict[str, str]] = {}
    with path.open() as fh:
        for line in fh:
            row = json.loads(line)
            rows[row["example_id"]] = row
            sid = row["latent"]["scenario_id"]
            variant = sid.rsplit(":", 1)[-1]
            if variant in ("poisoned", "clean"):
                pairs.setdefault(sid.rsplit(":", 1)[0], {})[variant] = row["example_id"]
    pairs = {k: v for k, v in pairs.items() if len(v) == 2}
    return rows, pairs


def load_scores(path: Path):
    raw, prob = {}, {}
    with path.open() as fh:
        for line in fh:
            row = json.loads(line)
            raw[row["example_id"]] = row.get("raw", {})
            prob[row["example_id"]] = row.get("probability", {})
    return raw, prob


def sign_test_p(wins: int, losses: int) -> float:
    n = wins + losses
    if n == 0:
        return float("nan")
    k = max(wins, losses)
    tail = sum(math.comb(n, i) for i in range(k, n + 1)) / 2**n
    return min(1.0, 2 * tail)


def bootstrap_auprc(y: np.ndarray, s: np.ndarray, rng, reps: int = 2000):
    point = average_precision_score(y, s)
    n = len(y)
    vals = []
    for _ in range(reps):
        idx = rng.integers(0, n, n)
        yy = y[idx]
        if yy.min() == yy.max():
            continue
        vals.append(average_precision_score(yy, s[idx]))
    lo, hi = np.percentile(vals, [2.5, 97.5])
    return point, lo, hi


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__)
        return 2
    rows, pairs = load_export(Path(argv[1]))
    longer = trust_differs = 0
    for ids in pairs.values():
        p, c = rows[ids["poisoned"]], rows[ids["clean"]]
        longer += observation_chars(p["context"]) > observation_chars(c["context"])
        trust_differs += p["latent"]["destination_trust"] != c["latent"]["destination_trust"]
    n_pairs = len(pairs)
    print(f"pairs: {n_pairs}")
    print(f"poisoned observation longer than clean: {longer}/{n_pairs} = {longer / n_pairs:.3f}")
    print(f"destination trust differs inside pair: {trust_differs}/{n_pairs} = {trust_differs / n_pairs:.3f}\n")

    print("| checker | wins | ties | losses | strict win | tie-adjusted win | sign test p | strict win, destination trust equal |")
    print("|---|---|---|---|---|---|---|---|")
    ci_rows = []
    rng = np.random.default_rng(0)
    for spec in argv[2:]:
        name, path = spec.split("=", 1)
        raw, prob = load_scores(Path(path))
        wins = ties = losses = 0
        same_wins = same_n = 0
        for ids in pairs.values():
            a = raw.get(ids["poisoned"], {}).get("prompt_injection_influence")
            b = raw.get(ids["clean"], {}).get("prompt_injection_influence")
            if a is None or b is None:
                continue
            same_trust = (
                rows[ids["poisoned"]]["latent"]["destination_trust"]
                == rows[ids["clean"]]["latent"]["destination_trust"]
            )
            same_n += same_trust
            if a > b:
                wins += 1
                same_wins += same_trust
            elif a == b:
                ties += 1
            else:
                losses += 1
        n = wins + ties + losses
        print(
            f"| {name} | {wins} | {ties} | {losses} | {wins / n:.3f} | "
            f"{(wins + ties / 2) / n:.3f} | {sign_test_p(wins, losses):.1e} | "
            f"{same_wins / same_n:.3f} (n={same_n}) |"
        )
        cells = []
        for dim in DIMS:
            ys, ss = [], []
            for eid, row in rows.items():
                lab = (row["labels"].get("values") or row["labels"]).get(dim)
                if lab not in ("yes", "no"):
                    continue
                s = prob.get(eid, {}).get(dim)
                if s is None:
                    s = raw.get(eid, {}).get(dim)
                if s is None:
                    continue
                ys.append(1 if lab == "yes" else 0)
                ss.append(float(s))
            y, s = np.array(ys), np.array(ss)
            if len(y) == 0 or y.min() == y.max():
                cells.append(f"n/a (n={len(y)})")
                continue
            point, lo, hi = bootstrap_auprc(y, s, rng)
            cells.append(f"{point:.3f} [{lo:.3f}, {hi:.3f}] (n={len(y)}, pos={y.mean():.3f})")
        ci_rows.append((name, cells))

    print("\n| checker | " + " | ".join(DIMS) + " |")
    print("|---|" + "---|" * len(DIMS))
    for name, cells in ci_rows:
        print(f"| {name} | " + " | ".join(cells) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
