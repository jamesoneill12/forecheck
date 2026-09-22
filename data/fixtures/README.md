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
  `adversarial.jsonl`, `heldout_policy_kind.jsonl`, `heldout_policy_phrasing.jsonl` —
  one `Example` per line, split leakage-safely by
  `forecheck.data.splitting.split_examples`: whole tools are withheld for
  `heldout_family`; groups whose policy predicates use a kind in
  `HELDOUT_POLICY_KINDS` are withheld for `heldout_policy_kind`; groups using a
  withheld paraphrase of an otherwise-trained kind are withheld for
  `heldout_policy_phrasing` (see ADR 0010); every other split is grouped by base
  scenario (template lineage root), never by row; both halves of a contrastive pair
  always land together and carry the same `contrastive_pair_id`.
- `<split>.manifest.json` — a `DatasetManifest` per split, produced by
  `forecheck.data.io.build_manifest`, recording row/family counts, a `sha256` of the
  JSONL file, and per-dimension positive rates. Verify with
  `uv run forecheck data verify data/fixtures`.

## Summary

- 1912 examples total: 1800 bulk scenarios (12 tool families x 150) plus 56 contrastive
  pairs, four per `ContrastiveAxis` member (112 rows).
- All 12 `ToolFamily` members and all 14 `ContrastiveAxis` members are represented.
- `PolicyPredicateKind` has 30 members (8 original, 7 added for policy-generalisation
  testing in ADR 0010, 15 more added in ADR 0011 to test whether "kind" itself becomes
  a unit of generalisation; see `docs/data-card.md`). `heldout_policy_kind` withholds 4
  kinds by default (`forecheck.data.splitting.default_heldout_policy_kinds`, up from 2).
- Split sizes at this scale: train 858, calibration 169, dev 182, test 157,
  heldout_family 235, adversarial 77, heldout_policy_kind 91, heldout_policy_phrasing
  143 (see `docs/data-card.md` for exact current counts and checksums). The heldout
  tier withholds 10 of the 72 catalogue tools, at least one per operation kind
  (`data/splitting.py::is_heldout_family`). Contrastive pairs route through their own
  eval-heavy ratio table (`data/splitting.py::PAIR_SPLIT_RATIOS`) so eval splits get
  more pair coverage than the base scenario ratios would give; at this small
  `pairs_per_axis=4` scale that still leaves a handful of axes with zero pairs in one
  particular eval split (see
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
