#!/usr/bin/env python3
"""Thin CI wrapper: ``forecheck data verify <dir>`` runnable without the console script.

Usage: ``uv run python scripts/check_no_leakage.py <data-dir>``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from forecheck.cli_cmds.data import verify


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print("usage: check_no_leakage.py <data-dir>", file=sys.stderr)
        return 2
    try:
        verify(Path(argv[0]))
    except typer.Exit as exc:
        return exc.exit_code or 0
    except typer.BadParameter as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
