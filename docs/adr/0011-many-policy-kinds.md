# ADR 0011 — Many policy kinds: testing whether "kind" can become a unit of generalisation

Status: accepted, 2026-09-22

## Context

`docs/results/synthetic-v2/README.md` ("Policy generalisation: decoder 2B on v3 and v4
data", ADR 0010) shows the 2B decoder trained on v3/v4 data generalises
`policy_conflict` to unseen policy *phrasings* (0.99 AUPRC) but not to unseen policy
*kinds*: withholding 2 of 15 kinds (`forbid_recipient_domain`, `data_residency_region`)
drops `policy_conflict` to 0.65-0.75 AUPRC / 0.59-0.77 AUROC on `heldout_policy_kind`,
while every other dimension on that split is unaffected. The README's own conclusion is
that the model has memorised the kinds it saw, not the general skill of checking a
natural-language predicate against a tool call, and names the fix: "many more kinds in
the generator (so kinds become the unit of generalisation, as phrasings did)".

With only 15 kinds (8 original + 7 added by ADR 0010), withholding even 2 removes a
meaningful fraction of the space, so the model has little basis to generalise the
*shape* of "check predicate X against field Y" rather than pattern-match one of a
short, mostly-memorised list. The hypothesis this ADR sets up to test: with enough
kinds, withholding a handful still leaves so many analogous kinds in training that
"kind" becomes learnable as a category of reasoning, the way wording already is.

## Decision

1. **15 new `PolicyPredicateKind` members**, taking the total from 15 to 30:
   `require_manager_approval_above_amount`, `forbid_currency`,
   `require_two_person_rule_for_destructive`, `forbid_tool_family_for_role`,
   `require_customer_consent_flag`, `forbid_export_format`, `forbid_channel`,
   `require_encryption_in_transit_flag`, `require_reason_field_nonempty`,
   `forbid_weekend_ops`, `require_recipient_verified_flag`,
   `require_data_classification_below`, `forbid_action_after_failed_auth_in_trajectory`,
   `max_records_per_day_quota`, `forbid_cross_tenant_reference`. Each is evaluated in
   `evaluate_predicate` (`forecheck.data.labeling`) purely from `LatentScenario`, and
   each deciding fact is rendered into the tool call or context so the label is
   observable in text, avoiding the class of bug in
   `docs/results/notes/privilege-escalation-diagnosis.md` (a label that depends on a
   latent field never rendered anywhere). Two candidates from the brief
   (`forbid_environment`, `require_data_classification_below`'s sibling
   `forbid_cross_tenant_reference` aside) were dropped or reshaped where they would
   have been mechanically identical to an existing kind (`forbid_in_stage`,
   `forbid_external_destination`) under a different name; `max_records_per_day_quota`
   was kept distinct from `forbid_bulk_above_n` by introducing a new cumulative
   `records_processed_today` fact rather than reusing the per-call `record_count`.
   Twelve new `LatentScenario` fields carry the new facts (`manager_approved`,
   `second_approver_present`, `customer_consent_given`, `encryption_in_transit`,
   `reason`, `channel`, `export_format`, `is_weekend`, `recipient_verified`,
   `failed_auth_in_trajectory`, `records_processed_today`, `cross_tenant_resource`),
   each rendered into the existing free-form `ProposedAction.arguments` dict,
   `Environment.labels`, `Destination.verified`, or a synthesized `TrajectoryStep` (for
   `failed_auth_in_trajectory`) by `forecheck.data.rendering`. None of these needed a
   new field on `ActionContext` itself, so `PROMPT_CONTRACT_VERSION` and
   `LABEL_DERIVATION_VERSION` are unchanged, matching ADR 0010's precedent. The original
   15 kinds' `evaluate_predicate` branches are untouched, so v3/v4 data stays comparable
   to v5 on every kind they share.
2. **Configurable `heldout_policy_kind` withholding.** `forecheck.data.splitting` gains
   `default_heldout_policy_kinds(n=4, *, salt=DEFAULT_SALT)`, which ranks all
   `PolicyPredicateKind` members by a salted hash and returns the lowest-ranked `n`,
   deterministically and without state (the same construction `is_heldout_family`
   already uses for tools). `HELDOUT_POLICY_KINDS` is now this function's output at the
   default `n=4` (up from the ADR 0010 hardcoded 2), and `split_examples` takes an
   optional `heldout_policy_kinds` override so an experiment can widen or narrow the
   withheld set without editing code. `forecheck data split` exposes
   `--n-heldout-policy-kinds` (default 4), and the chosen kinds are recorded as
   `heldout_policy_kinds` on every split's `DatasetManifest` so the withheld set for a
   given dataset is auditable from the manifest alone. `heldout_policy_phrasing`
   (`HELDOUT_PARAPHRASE_INDICES = {3}`) is unchanged.
3. **v5 recipe.** `configs/eks/train-2b-b200-v5-recipe.yaml` is v4 with `v4` -> `v5`
   throughout (data dir, run name, experiment name), generating from
   `configs/data/train_medium.yaml` (unchanged) against the new 30-kind generator and
   the new 4-kind default withhold.

## What the v5 experiment tests

Train the same 2B decoder recipe on v5 data (30 kinds, 4 withheld by default) and
compare `policy_conflict` on `heldout_policy_kind` against the v4 numbers above (0.752
AUPRC / 0.77 AUROC, 15 kinds, 2 withheld). The hypothesis is that AUPRC/AUROC on
`heldout_policy_kind` rises substantially closer to the `heldout_policy_phrasing` /
`test` numbers (~0.99), because 26 remaining training kinds give the model enough
instances of "evaluate this predicate against that rendered fact" to learn the
operation, not memorise a lookup table of 13 (15 minus the old 2). `test`,
`heldout_family`, and `heldout_policy_phrasing` on `policy_conflict`, and every other
`RiskDimension`, should be roughly unchanged from v4 — this ADR's changes are additive
to the kind space, not to any existing kind's semantics.

## What would falsify the hypothesis

If `heldout_policy_kind` AUPRC on v5 stays in the 0.65-0.75 band despite 30 kinds and
only 4 withheld (a smaller withheld *fraction* than v3/v4's 2/15), the "kind becomes a
unit of generalisation with enough kinds" story is wrong, and the deficit is more
likely structural — e.g. the model needs an explicit retrieval-plus-entailment
formulation for policy text rather than a bigger training kind inventory, as the
README's alternative hypothesis suggested. A rise that is proportional to the reduced
withheld *fraction* alone (rather than to the increase in kind *diversity*) would also
be inconclusive and suggest re-running v5 with a much larger `n` in
`default_heldout_policy_kinds` (e.g. withhold 10-12 of 30) to separate the two effects.

## Consequences

- `PolicyPredicateKind` is now large enough that adding a policy-kind-conditioned
  feature elsewhere (rule baseline, policy DSL) should iterate over the enum rather than
  enumerate members by hand; `evaluate_predicate`'s `test_every_kind_is_handled_explicitly`
  and `_POLICY_CLAUSE_TEMPLATES`'s four-paraphrase-per-kind test already do this and
  needed no changes to cover the 15 new kinds.
- `data/fixtures/` was regenerated via the documented CLI
  (`forecheck data generate --offline --config configs/data/fixtures.yaml`,
  `forecheck data split`, `forecheck data verify`) against the new generator and
  default 4-kind withhold; per-dimension label counts for `policy_conflict` on
  `heldout_policy_kind` were checked non-degenerate (both `yes` and `no` present) before
  committing.
- Widening `heldout_policy_kind` (or narrowing it) for a follow-up experiment is now a
  CLI flag, not a code change.
