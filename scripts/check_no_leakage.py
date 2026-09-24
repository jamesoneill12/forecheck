#!/usr/bin/env python3
"""Thin CI wrapper: ``forecheck data verify <dir>`` runnable without the console script,
plus label-leakage checks that ``forecheck data verify`` does not cover (argument-key
presence parity between injected and non-injected calls; a token denylist).

Usage: ``uv run python scripts/check_no_leakage.py <data-dir>``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from forecheck.cli_cmds.data import verify
from forecheck.contracts import ActionOrigin, Example
from forecheck.data.io import read_jsonl

_DENYLIST_TOKENS: tuple[str, ...] = ("attacker", "instructed_target", "shadow-ops")
_KEY_RATE_TOLERANCE = 0.05


def _load_examples(directory: Path) -> list[Example]:
    raw_path = directory / "raw.jsonl"
    if raw_path.exists():
        return read_jsonl(raw_path)
    examples: list[Example] = []
    for path in sorted(directory.glob("*.jsonl")):
        examples.extend(read_jsonl(path))
    return examples


def _check_denylist(examples: list[Example]) -> list[str]:
    failures = []
    for example in examples:
        lowered = example.model_dump_json().lower()
        for token in _DENYLIST_TOKENS:
            if token in lowered:
                failures.append(f"{example.example_id}: denylisted token {token!r} found")
    return failures


def _check_argument_key_rate_parity(examples: list[Example]) -> list[str]:
    """Every argument key's presence rate, pooled across tool kinds, must be within
    ``_KEY_RATE_TOLERANCE`` between injected_instruction calls and everything else."""
    injected_counts: dict[str, int] = {}
    other_counts: dict[str, int] = {}
    n_injected = 0
    n_other = 0
    for example in examples:
        is_injected = example.latent.action_origin is ActionOrigin.INJECTED_INSTRUCTION
        counts = injected_counts if is_injected else other_counts
        n_injected += is_injected
        n_other += not is_injected
        for key in example.context.proposed_action.arguments:
            counts[key] = counts.get(key, 0) + 1
    if n_injected == 0 or n_other == 0:
        return []
    failures = []
    for key in sorted(set(injected_counts) | set(other_counts)):
        rate_injected = injected_counts.get(key, 0) / n_injected
        rate_other = other_counts.get(key, 0) / n_other
        diff = abs(rate_injected - rate_other)
        if diff >= _KEY_RATE_TOLERANCE:
            failures.append(
                f"argument key {key!r}: injected={rate_injected:.3f} other={rate_other:.3f} "
                f"diff={diff:.3f} >= {_KEY_RATE_TOLERANCE}"
            )
    return failures


def main(argv: list[str]) -> int:
    expect_leak = "--expect-leak" in argv
    argv = [a for a in argv if a != "--expect-leak"]
    if len(argv) != 1:
        print("usage: check_no_leakage.py [--expect-leak] <data-dir>", file=sys.stderr)
        return 2
    directory = Path(argv[0])
    examples = _load_examples(directory)
    if not examples:
        print(f"FAIL: no examples found under {directory}", file=sys.stderr)
        return 1

    leak_failures = _check_denylist(examples) + _check_argument_key_rate_parity(examples)
    if expect_leak:
        # Control arms that deliberately keep the v1-v5 leak must still contain it.
        failures = [] if leak_failures else ["--expect-leak set but no leak detected"]
    else:
        failures = leak_failures
    for failure in failures:
        print(f"FAIL: {failure}", file=sys.stderr)

    manifests_present = any(directory.glob("*.manifest.json"))
    if manifests_present:
        try:
            verify(directory)
        except typer.Exit as exc:
            if exc.exit_code:
                failures.append("forecheck data verify reported failures (see above)")
        except typer.BadParameter as exc:
            print(f"FAIL: {exc}", file=sys.stderr)
            failures.append(str(exc))

    if failures:
        return 1
    n_note = "" if manifests_present else " (pre-split raw dataset; split-leakage check skipped)"
    leak_note = (
        f"leak present as expected ({len(leak_failures)} findings)"
        if expect_leak
        else "no denylisted tokens; key-rate parity held"
    )
    print(f"OK: {len(examples)} examples checked; {leak_note}{n_note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
