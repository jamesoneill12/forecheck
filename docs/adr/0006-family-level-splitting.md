# ADR 0006 — Splits are taken on scenario family and template ancestry, never on rows

Status: accepted, 2026-09-20

## Context

Synthetic datasets leak trivially under random row splits: two renderings of the same
latent scenario, or the two halves of a contrastive pair, land on opposite sides and
inflate held-out accuracy.

## Decision

The split key is the root of `template_lineage`, falling back to `family_id`. Groups are
hashed with a fixed salt and assigned to `train / calibration / dev / test /
heldout_family / adversarial` by deterministic ratio. Both halves of a contrastive pair
share a group. `assert_no_leakage` runs at manifest time and in CI. Rows with
`usage = eval_only` or a benchmark canary are refused from `train` and `calibration`.

## Consequences

Held-out numbers measure generalization across scenario families, not memorization of
templates. Manifests carry a digest of the family-id list so leakage between separately
built artefacts is detectable without shipping the ids.
