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

## Amended 2026-09-21

The original decision hashed one key, `template_lineage[0]`, straight into all six
splits including `heldout_family`. In generation, `family_id` was `f"{family}:{tool}"`
and `template_lineage` was `[family_id]`, so the split key was actually a whole *tool*
rather than a scenario. On a 50k-row generation this produced a test split covering
only 10 tools, and all three `is_communication=True` tools landed in train — every
`external_communication` label in calibration/test/heldout was `not_applicable`. A
tool-level hash cannot do better: with one key per tool, any deterministic partition
either puts a tool entirely in one split or not, so dimensions carried by only a
handful of tools have no guaranteed eval coverage.

The fix splits on two independent tiers instead of one key:

1. **Heldout-family tier** (`is_heldout_family`): a separate hash of `family_id` alone
   sends `HELDOUT_FAMILY_RATIO` (5%) of *tools*, in their entirety, to
   `heldout_family`. This preserves the original intent of that split — whole tools
   never seen in training — as its own decision.

   *Amendment 2026-09-21 (b).* The first GPU run withheld three tools by plain hash;
   none performed a `grant`, so `heldout_family` had zero `privilege_escalation`
   positives and `external_communication` had no evaluable rows. Selection is now
   stratified by `OperationKind`: within each kind the `max(1, round(0.12 * n))`
   lowest-hashing catalogue tools are withheld (10 of 72), so every operation, and
   every label dimension driven by one, has an unseen tool. Family ids outside the
   catalogue keep the plain hash threshold.
2. **Group tier** (`assign_split`): `template_lineage` now roots at
   `f"{family_id}#{scenario_id}"`, one base scenario (and its contrastive
   derivatives) rather than a whole tool. Everything not pulled into
   `heldout_family` is split at this finer grain over train / calibration / dev /
   test / adversarial, so a tool's many scenarios spread across splits instead of
   moving as a block.

`assign_split`'s ratios (`SPLIT_RATIOS`) no longer include `heldout_family`; they are
the original train/calibration/dev/test/adversarial weights renormalised to sum to 1
after removing the 5% now spent by the heldout-family tier. `assert_no_leakage` gained
a check that a family routed to `heldout_family` never also appears in another split.
