# Research direction (as of 2026-09-22)

What the first day of experiments says about where forecheck is unique, what is still
unproven, and what to run next. Numbers come from `docs/results/synthetic-v2/README.md`;
all are on synthetic data.

## The claim that survived

**Pre-execution risk for agent tool calls is mostly a delegated-authority problem, not a
content-safety problem, and general safety models do not solve it.**

Evidence:

- Stripping identity (principal entitlements, delegated scopes, policy text) from the
  input drops the trained 2B decoder from 0.915 to 0.736 macro AUPRC on held-out tools.
  Three dimensions collapse to chance: `unauthorized_scope` (1.00 to 0.12),
  `policy_conflict` (0.999 to 0.35), `insufficient_context` (0.85 to 0.42).
- The dimensions that survive stripping (`untrusted_destination`, `financial_commitment`,
  `external_communication`, `destructive`) are the ones the rule baseline already scores
  at 1.0. They are lookups, not learning. `prompt_injection_influence` and
  `suspicious_action_sequence` are the only content-style dimensions where the model beats
  rules (0.81 vs 0.30, 0.95 vs 0.33).
- Two aligned safety models with the policy in their prompt sit at chance on exactly the
  identity dimensions and are unaffected by stripping: Granite Guardian 3.3 8B (macro
  ~0.25), gpt-oss-safeguard 20B (~0.27, and ~50x slower per row). They read the action;
  they do not reason about who is allowed to do it on whose behalf.

So the product is not "a guardrail for agents". It is a **delegated-authority conformance
checker**: given who the agent acts for, what it was delegated, and what the policy says,
is this specific call inside the envelope. That framing has no incumbent among the
safety-model vendors, and rule engines (OPA/Cedar) cannot cover the learned dimensions or
paraphrased policies.

## The second claim, half proven

**Calibrated per-dimension probabilities plus an expected-cost decision rule let many
policies stack without becoming conservative.**

- Threshold stacking of three policies pushes FPR from 0.14 to 0.97 (deny nearly
  everything). This is the failure DynamoGuard customers hit when running many guards.
- Expected-cost aggregation over the same probabilities is invariant to the number of
  policies (FPR 0.082 / FNR 0.070 from k=2 to k=8).
- But the level it settles at depends on calibration sharpness: the encoder's flatter
  probabilities give FPR 0.92 under the same rule. Composition is a property of the
  calibrated model plus the engine, not the engine alone.

Unproven: the cost table is the default severity-tier table, untuned, and the k=1 row
shows it trades FPR for FNR against the F1-optimal threshold. A tuned table on a
realistic approval-cost model is the next step (see approval elimination below).

## Policy generalisation: the result we are waiting on

ADR 0010 adds seven policy predicate kinds with four paraphrases each and two splits:
unseen kinds and unseen phrasings. The encoder shows no drop on either (0.848 / 0.832 vs
0.828 test), but the encoder never learned `policy_conflict` in the first place (~0.45),
so it cannot tell us whether a model that reads the policy generalises. The decoder v3 job
(pending) is the real test. If `policy_conflict` holds above ~0.9 on unseen kinds, the
"one model, customer-written policies, no per-policy fine-tune" claim is supported on
synthetic data. If it drops, the fix is more kinds and paraphrases in the generator, and
the paper claim becomes "generalises across phrasing, not across kind".

## Metrics that make the business case

Existing safety-model metrics (AUPRC on unsafe content) do not measure what a buyer pays
for. Two replacements, both specified in `docs/evaluation/approval-elimination.md`:

1. **Approvals eliminated at a fixed incident rate.** For a deployment where every
   sensitive action currently goes to a human, what fraction can be auto-allowed while the
   rate of allowed-but-risky actions stays under a budget. This is a curve over the budget,
   read off the calibrated probabilities. Not implemented yet.
2. **Delegated-authority conformance.** Recall on `unauthorized_scope` and
   `policy_conflict` at the operating point chosen by (1). This is the number no
   competitor reports.

## What the agent-self-judgment eval will settle

`configs/eks/eval-agent-self-b200-recipe.yaml` (landed, not yet run) gives a Fin-style
agent the same policy and delegation context and asks PROCEED or STOP. If the 8B agent
scores near the external classifier on the identity dimensions, the product story is
"cheap external audit", not "capability the agent lacks". If it sits near the guardian
baselines, the external checker is load-bearing. Either answer is useful; the second is
the stronger paper.

## Novelty, honestly assessed

- Learned, calibrated, per-dimension scoring conditioned on delegation context, with
  identity ablation as the diagnostic: not in the guardrail literature we know of
  (Llama Guard, Granite Guardian, ShieldGemma, Aegis score content; AgentDojo/InjecAgent
  score injection outcomes; policy engines are deterministic).
- Expected-cost composition of many policies over calibrated probabilities, with the
  k-invariance result: not novel as decision theory, novel as a guardrail-stacking
  result and directly answers the over-conservatism problem.
- Held-out-policy-kind generalisation as a benchmark split: novel framing, pending result.

## Known threats

- Synthetic data only. The generator encodes the label function; template regularities
  inflate every number. The v1 lesson (7 of 11 dims were template lookups) still applies
  to 4 of them.
- `privilege_escalation` was unobservable in v2/v3 text (render defect, fixed for v4).
- Generator seed nondeterminism (fixed 2026-09-22) means v2 and v3 are not byte
  reproducible from their configs.
- Fin action taxonomy in `docs/fin-action-mapping.md` is inferred, not from a spec.

## Run order from here

1. Decoder v3 policy-generalisation reports (running).
2. v4 decoder on fixed data; Guardian 3.3 8B as a LoRA base (both running).
3. Agent self-judgment eval, 2B and 8B, with and without identity (ready to submit).
4. Approval-elimination curve on the decoder's heldout probabilities.
5. Real-data probe: 200 hand-labelled Fin-shaped tool calls through the v4 model, to
   size the synthetic-to-real gap before any further scaling.
