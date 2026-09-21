# ADR 0010 — Policy-generalisation splits: heldout policy kind and phrasing

Status: accepted, 2026-09-21

## Context

The product thesis is a policy-conditioned classifier that generalises to a new
customer's policy text zero-shot. The existing splits (ADR 0006) measure
generalisation across scenarios and whole tools, but never test whether the model
learned the *shape* of `policy_conflict` reasoning or just memorised the eight policy
kinds and their exact clause wordings seen in training.

## Decision

1. **More policy kinds.** `PolicyPredicateKind` gains seven members
   (`forbid_bulk_above_n`, `require_ticket_reference`, `forbid_outside_business_hours`,
   `forbid_recipient_domain`, `require_dry_run_first`, `data_residency_region`,
   `forbid_pii_field_export`), each evaluable from `LatentScenario` alone
   (`evaluate_predicate` in `forecheck.data.labeling`) and each with its deciding
   latent fact rendered into the context: `record_count` (existing), `local_hour` and
   `resource_region` (via `Environment.labels`/`.region`), `recipient_domain` (via
   `Destination.identifier`), `ticket_reference`/`touched_pii_fields` (via
   `ProposedAction.arguments`), and `dry_run_performed` (via an appended
   `TrajectoryStep`). None of these required a change to `contracts.context`, so
   `PROMPT_CONTRACT_VERSION` is untouched.
2. **Phrasing diversity.** Every kind (old and new) has four clause paraphrases
   (`_POLICY_CLAUSE_TEMPLATES` in `forecheck.data.rendering`). `PolicyPredicate` gains
   `paraphrase_index`, sampled by the generator's seeded rng and carried on the latent
   predicate itself, so splitting can key on wording without touching rendered text.
3. **Two new splits**, added as `Split` members and produced by `forecheck data
   split`:
   - `heldout_policy_kind`: any group whose policy predicates include
     `HELDOUT_POLICY_KINDS` (`forbid_recipient_domain`, `data_residency_region`, fixed
     constants in `forecheck.data.splitting`). Never appears in
     train/calibration/dev/test.
   - `heldout_policy_phrasing`: any group whose predicates use a trained kind with a
     withheld paraphrase index (`HELDOUT_PARAPHRASE_INDICES = {3}`). Never appears in
     train.

   Routing checks `is_heldout_family` first, so the existing heldout-family invariant
   (ADR 0006) is unchanged; only groups outside a heldout family are diverted into the
   two new tiers. Both are keyed on `compute_group_key`, so contrastive pairs still
   never straddle a split.

## Consequences

- `heldout_policy_kind` measures generalisation to a policy *kind* never seen in
  training; `heldout_policy_phrasing` measures generalisation to unseen *wording* of a
  kind the model did train on. Together they isolate whether failures come from novel
  semantics or from novel surface form.
- At `configs/data/train_medium.yaml` scale both splits clear several thousand rows
  with hundreds of `policy_conflict` positives and negatives each (measured directly,
  see `tests/generation/test_policy_generalisation_splits.py` for the fixture-scale
  regression floor of "nonzero and both label values present").
- `LABEL_DERIVATION_VERSION` and `PROMPT_CONTRACT_VERSION` are both unchanged: the new
  kinds extend `evaluate_predicate` additively and every new fact rides on an existing
  `ActionContext` field.
