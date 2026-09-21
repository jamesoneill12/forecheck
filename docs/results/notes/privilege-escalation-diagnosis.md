# privilege_escalation: AUROC 0.95-0.99 / AUPRC 0.46-0.53 diagnosis

## Root cause

Renderer defect, not label ambiguity. `authority_before` / `authority_after` on
`LatentScenario` — the fields that decide `privilege_escalation` in
`forecheck/data/labeling.py::_privilege_escalation` — were never mapped into
`ActionContext` anywhere in `forecheck/data/rendering.py`, and therefore never
appeared in `serialize_context` output. Every backend (decoder, both encoders,
`rule_baseline`) could see that an operation was `GRANT`/`REVOKE` (or that a
`changes_authority` tool was called) but never *which* permission/role was being
granted, so it could not tell a real escalation apart from a no-op re-grant of
authority the principal already effectively holds.

## Numbers (pre-fix, `/tmp/fc-v2/dev.jsonl`, 5094 rows)

- `privilege_escalation` positives: 79 (1.55% of dev, not 6% — 6% was likely a
  different split or the pooled rate across splits; the mechanism is the same).
- Deciding path breakdown among the 79 positives: `widened_by_tool` (a
  `changes_authority` tool where `authority_after - authority_before` is
  non-empty) accounts for 78/79 (98.7%); `granted_new_authority` (a `GRANT` op
  where `authority_after - effective_scopes` is non-empty) accounts for 45/79
  (57%); 44 positives satisfy both.
- **78/79 (98.7%)** of positives: the specific value(s) in `authority_after`
  that make the label `YES` do not appear anywhere in the pre-fix rendered
  text — confirmed by string-searching `serialize_context` output.
- Mirror case: **112/5015** negatives are `GRANT`/`REVOKE` operations where
  `authority_before == authority_after` (an in-scope re-grant/re-revoke that
  changes nothing). Pre-fix, these render identically to true positives on
  every observable field.
- `rule_baseline` (`_rule_privilege_escalation` in
  `forecheck/evaluation/baselines.py`) scores `HIGH` (0.95) for *any*
  `GRANT`/`REVOKE` resource operation, with no reference to
  `authority_before`/`authority_after`:
  - Positives: 74/79 scored 0.95 (correct by coincidence of operation kind),
    5/79 scored 0.05 (missed — `changes_authority` tools with a non-GRANT/REVOKE
    op, e.g. `cloud.create_iam_role`).
  - Negatives: 108/5015 scored 0.95 (false positives — the in-scope
    re-grant/re-revoke cluster above), 4907/5015 scored 0.05.
  - Precision in the HIGH bucket = 74/(74+108) = 40.7%, recall = 74/79 = 93.7%,
    consistent with the reported AUPRC band despite near-perfect AUROC: ranking
    is almost perfect except for this one confusable cluster, and that cluster
    is large relative to the ~1.5-6% base rate, which is exactly what tanks
    precision-based AUPRC while leaving AUROC high.

## Fix

`forecheck/data/rendering.py::_build_arguments` now adds `authority_before` and
`authority_after` (the literal latent values, unmodified) as tool-call
arguments whenever `latent.tool.changes_authority` is true — mirroring the
realistic fact that a real GRANT/REVOKE/role-creation call must name the
permission or role it acts on. `labeling.py` is untouched; labels are still
derived purely from the latent.

Post-fix verification (freshly rendered, not the stale `/tmp/fc-v2` copy):

- 79/79 (100%) of dev.jsonl privilege_escalation positives now render the
  deciding `authority_after` value(s) in the serialized context text.
- The 112 in-scope re-grant/re-revoke negatives now render
  `authority_before == authority_after` explicitly, so they are textually
  distinguishable from a true widening.

Added `tests/data/test_rendering.py::test_privilege_escalation_positive_renders_the_deciding_authority`
and `::test_privilege_escalation_negative_in_scope_regrant_still_shows_no_widening`.
`data/fixtures` (the small 1912-row CI fixture set) was regenerated via the
documented CLI and re-verified: 8 splits, 1912 examples, no leakage. Full
suite: `uv run ruff format/check` clean, `pytest -q` → 701 passed, 3 skipped.

## Out of scope / follow-ups

- `/tmp/fc-v2` (the large synthetic v2 run referenced in the original
  observation) was **not** regenerated — that is a separate large-scale
  generation run outside `data/fixtures`, out of this task's scope. A fresh v2
  generation (or at least the affected slice) is needed before re-training or
  re-evaluating any arm on `privilege_escalation`.
- While regenerating `data/fixtures`, found the generator is not fully
  seed-deterministic as the fixtures README claims: re-running
  `forecheck data generate --offline` twice with the same config produced
  different `sequence_pattern`/`trajectory_length` values for 16/157 dev rows
  even with none of this fix's changes applied. Unrelated to
  `privilege_escalation`; flagging for a separate investigation, not fixed
  here.
