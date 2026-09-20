# Contributing

## Setup

```bash
uv sync --extra dev
uv run pre-commit install
make check          # ruff, mypy, pytest
```

Python 3.12+. Everything in the default test suite runs offline with no GPU and no API
key. Tests that need either are marked `gpu`, `network` or `api_key` and are skipped
unless the resource is present.

## What we accept

- Fixes with a failing test first.
- New scenario generators, tool catalogue entries and contrastive axes — with the
  corresponding `derive_labels` rules unit-tested both ways.
- New evaluation slices and metrics.
- Policy bundle improvements, provided no rule denies on tool name alone (ADR 0007).
- Backends implementing `ClassifierBackend`.

## What we do not accept

- Any change that lets a response carry a `probability` without a loaded calibration
  artifact.
- A `decision` field on `ClassifyResponse`, or model access inside the policy engine
  (ADR 0001).
- Training-data contributions derived from a benchmark marked evaluation-only, or
  containing a canary string.
- Benchmark results without the evaluation class (`synthetic_in_distribution`,
  `synthetic_heldout_adversarial`, `external_or_human`) stated.

## Style

Ruff and mypy `--strict` are enforced. Rationale goes in docstrings, not comments;
docstrings stay short. Every module states what it is for in its first line. Public
behaviour changes need an ADR in `docs/adr/` and a `CHANGELOG.md` entry.

## Commits and pull requests

Small, single-purpose commits. The PR description should say what changed and why, and
which tests demonstrate it. CI must be green.

## Licence

By contributing you agree your contribution is licensed under Apache-2.0.
