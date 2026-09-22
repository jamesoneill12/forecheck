# Generator determinism: sequence_pattern / trajectory_length reproducibility

## Root cause

`forecheck/generation/scenarios.py` built its attack-sequence candidate list with
`_ATTACK_SEQUENCE_LIST = tuple(ATTACK_SEQUENCE_PATTERNS)`, where
`ATTACK_SEQUENCE_PATTERNS` (`forecheck/contracts/latent.py`) is a `frozenset` of
`SequencePattern` members. `SequencePattern` is a `StrEnum`, so its members hash as
plain strings, and Python randomizes string hashing per process by default
(`PYTHONHASHSEED` unset). Iterating a `frozenset` of such members therefore yields a
different order in every process, even for byte-identical code and the same
`master_seed`.

`_sample_sequence()` calls `rng.choice(_ATTACK_SEQUENCE_LIST)` to pick an attack
pattern. `rng.choice` consumes the same number of RNG draws regardless of list order,
so the bug never desynchronized the RNG stream (which is why almost everything else in
a scenario stayed identical) — it just mapped the same random index to a different
`SequencePattern` member depending on which process generated it. This showed up as
`latent.sequence_pattern` (and the `context.trajectory` text derived from it in
`rendering.py`) differing for ~5% of rows (98/1912 in the `fixtures.yaml` run) between
two otherwise-identical `forecheck data generate` invocations. Every other use of
`ATTACK_SEQUENCE_PATTERNS` in the codebase is an `in` membership check, which is
order-independent, so this was the only affected call site.

## Fix

`src/forecheck/generation/scenarios.py`: sort the frozenset into a stable tuple before
it is indexed —

```python
_ATTACK_SEQUENCE_LIST: tuple[SequencePattern, ...] = tuple(sorted(ATTACK_SEQUENCE_PATTERNS))
```

`StrEnum` members compare and sort as their string values, so this is a fixed,
process-independent order. `rng.choice` still selects uniformly at random among the
same six patterns, so label semantics and the sampling distribution are unchanged —
only which process a given RNG draw resolves to is now fixed.

## Verification

- Reproduced pre-fix: generated `configs/data/fixtures.yaml` twice into separate
  directories and diffed by `example_id`. 1912/1912 ids matched; of those, 98 rows
  differed on `latent.sequence_pattern` and `context.trajectory` (plus 4-viewer-level
  incidental fields downstream of it), with `provenance.created_at` (wall clock)
  differing on every row as expected.
- Confirmed the mechanism directly: ran a small generation script twice via
  `subprocess` with `PYTHONHASHSEED=0` vs `PYTHONHASHSEED=1` (and other seed pairs).
  Pre-fix, output bytes differed on every pair tried; post-fix, output bytes were
  identical (module a fixed `now_fn` so `created_at` doesn't confound the comparison).
- Added `tests/data/test_generation_determinism.py::test_generation_is_byte_identical_across_hash_seeds`,
  which generates a small dataset via two subprocesses with `PYTHONHASHSEED=0` and
  `PYTHONHASHSEED=1` and asserts the emitted `raw.jsonl` bytes are identical. Verified
  it fails against the pre-fix code and passes against the fix.
- Regenerated `data/fixtures` via the documented CLI
  (`forecheck data generate --offline --config configs/data/fixtures.yaml --out data/fixtures`,
  `forecheck data split data/fixtures`) and reverified with `forecheck data verify
  data/fixtures`: 8 splits, 1912 examples, no leakage, no eval_only/canary rows in
  train/calibration.
- Full suite: `uv run ruff check` / `uv run ruff format --check` clean;
  `uv run pytest -q` → 702 passed, 3 skipped (701 + the new regression test).
