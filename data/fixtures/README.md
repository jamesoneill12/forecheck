# Synthetic fixture dataset

Every row in this directory is **wholly synthetic**. There is no real user data, no real
credentials, and no content sourced from an external benchmark: each `Example` is
generated end-to-end from a randomly sampled `LatentScenario` via
`forecheck.generation.pipeline.GenerationPipeline` using the offline template renderer
(`forecheck.generation.renderers.OfflineTemplateRenderer`), which never makes a network
call. Labels are derived deterministically from the latent scenario by
`forecheck.data.labeling.derive_labels` — never inferred from the rendered text.

## Contents

- `train.jsonl`, `calibration.jsonl`, `dev.jsonl`, `test.jsonl`, `heldout_family.jsonl`
  — one `Example` per line, split leakage-safely by
  `forecheck.data.splitting.split_examples` (grouped by scenario-family / template
  ancestry, never by row; both halves of a contrastive pair always land together, and
  both halves carry the same `contrastive_pair_id`). This seed produced no rows for the
  `adversarial` split; that is an expected outcome of the same deterministic assignment
  used everywhere else, not a special case.
- `<split>.manifest.json` — a `DatasetManifest` per split, produced by
  `forecheck.data.io.build_manifest`, recording row/family counts, a `sha256` of the
  JSONL file, and per-dimension positive rates. Verify with
  `uv run forecheck data verify data/fixtures`.

## Summary

- 748 examples total: 720 bulk scenarios (12 tool families x 60) plus 14 contrastive
  pairs, one per `ContrastiveAxis` member (28 rows).
- All 12 `ToolFamily` members and all 14 `ContrastiveAxis` members are represented.
- 46.9% of rows have an all-`NO`/`NOT_APPLICABLE` label set (benign hard negatives).
- Split sizes: train 455, calibration 61, dev 113, test 95, heldout_family 24.

## Regenerating

Generation is deterministic in a fixed master seed: the same seed reproduces identical
`example_id`s and labels (only `provenance.created_at` and manifest timestamps vary).
The job list is defined by `configs/data/fixtures.yaml` (a
`forecheck.generation.config.GenerationConfig`).

```
uv run forecheck data generate --offline --config configs/data/fixtures.yaml --out data/fixtures
uv run forecheck data split data/fixtures
uv run forecheck data verify data/fixtures
```

or simply `make fixtures`.
