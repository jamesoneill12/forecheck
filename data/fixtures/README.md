# Synthetic fixture dataset

Every row in this directory is **wholly synthetic**. There is no real user data, no real
credentials, and no content sourced from an external benchmark: each `Example` is
generated end-to-end from a randomly sampled `LatentScenario` via
`forecheck.generation.pipeline.GenerationPipeline` using the offline template renderer
(`forecheck.generation.renderers.OfflineTemplateRenderer`), which never makes a network
call. Labels are derived deterministically from the latent scenario by
`forecheck.data.labeling.derive_labels` — never inferred from the rendered text.

## Contents

- `train.jsonl`, `calibration.jsonl`, `dev.jsonl`, `test.jsonl`, `heldout_family.jsonl`,
  `adversarial.jsonl` — one `Example` per line, split leakage-safely by
  `forecheck.data.splitting.split_examples`: whole tools are withheld for
  `heldout_family`; every other split is grouped by base scenario (template lineage
  root), never by row; both halves of a contrastive pair always land together and carry
  the same `contrastive_pair_id`.
- `<split>.manifest.json` — a `DatasetManifest` per split, produced by
  `forecheck.data.io.build_manifest`, recording row/family counts, a `sha256` of the
  JSONL file, and per-dimension positive rates. Verify with
  `uv run forecheck data verify data/fixtures`.

## Summary

- 1912 examples total: 1800 bulk scenarios (12 tool families x 150) plus 56 contrastive
  pairs, four per `ContrastiveAxis` member (112 rows).
- All 12 `ToolFamily` members and all 14 `ContrastiveAxis` members are represented.
- 43.4% of rows have an all-`NO`/`NOT_APPLICABLE` label set (benign hard negatives).
- Split sizes: train 1016, calibration 184, dev 199, test 189, heldout_family 237,
  adversarial 87. The heldout tier withholds 10 of the 72 catalogue tools, at least one
  per operation kind (`data/splitting.py::is_heldout_family`). Contrastive pairs route through their own eval-heavy ratio table
  (`data/splitting.py::PAIR_SPLIT_RATIOS`) so eval splits get more pair coverage than
  the base scenario ratios would give; at this small `pairs_per_axis=4` scale that still
  leaves a handful of axes with zero pairs in one particular eval split (see
  `tests/data/test_splitting.py::test_pair_group_routes_through_pair_ratios` and
  `configs/data/train_medium.yaml`, which raises `pairs_per_axis` to reliably clear a
  per-split floor at generation scale).

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
