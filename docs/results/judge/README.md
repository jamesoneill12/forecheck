# Independent LLM-judge labels on v4 (gpt-5.6-sol via Codex)

Are the generator's labels recoverable by a blind reader of the rendered text? A frontier
model judged 600 v4 examples (stratified so every dimension has at least 20 yes and 20 no
rows; splits heldout_family, heldout_policy_kind, test) given only the rendered context and
the eleven dimension definitions, never the latent scenario or the generator label. Method:
`docs/evaluation/llm-judge-labels.md`. Files: `v4-sample.jsonl`, `coverage.json`,
`v4-labels-gpt56.jsonl` (600/600 parsed first try), `agreement-gpt56/`,
`v4-labels-gpt56-noid.jsonl` (identity-stripped re-judging of the same rows),
`agreement-gpt56-noid/`.

The judge is one LLM reading the same text a classifier sees, so agreement measures label
observability, not ground truth (see the method doc). Low agreement is the informative case.

## Agreement, yes vs not-yes

The judge often answers `not_applicable` where the generator says `no` (and vice versa);
the three-way kappa in `agreement-gpt56/agreement.md` is dominated by that convention gap.
The table below collapses `no` and `not_applicable` into "not yes", which is the question
that matters for a positive-class detector.

| dimension | kappa | agreement | generator yes | judge yes | judge recall of generator yes | judge precision |
|---|---|---|---|---|---|---|
| prompt_injection_influence | 0.905 | 0.983 | 63 | 53 | 0.84 | 1.00 |
| privilege_escalation | 0.909 | 0.988 | 38 | 45 | 1.00 | 0.84 |
| policy_conflict | 0.714 | 0.862 | 228 | 259 | 0.89 | 0.78 |
| destructive_or_irreversible_action | 0.511 | 0.897 | 68 | 76 | 0.60 | 0.54 |
| suspicious_action_sequence | 0.404 | 0.852 | 49 | 120 | 0.82 | 0.33 |
| unauthorized_scope | 0.391 | 0.800 | 81 | 159 | 0.74 | 0.38 |
| financial_commitment | 0.359 | 0.935 | 50 | 13 | 0.24 | 0.92 |
| external_communication | 0.331 | 0.897 | 21 | 77 | 0.86 | 0.23 |
| untrusted_destination | 0.213 | 0.777 | 85 | 119 | 0.41 | 0.29 |
| insufficient_context | 0.059 | 0.843 | 58 | 52 | 0.14 | 0.15 |
| sensitive_data_exposure | 0.002 | 0.783 | 48 | 98 | 0.17 | 0.08 |

n = 600 for every row. Recomputed from `v4-labels-gpt56.jsonl` and `v4-sample.jsonl`.

## Reading

Three tiers.

**Recoverable (kappa above 0.7): `prompt_injection_influence`, `privilege_escalation`,
`policy_conflict`.** A blind reader recovers these from the text. `privilege_escalation`
at 0.91 confirms the v4 render fix: the label is now in the tool-call arguments.
`policy_conflict` at 0.71 with judge recall 0.89 means the policy text plus the call is
enough to spot a conflict; the 56 generator-no / judge-yes rows are mostly the judge
reading a policy more strictly than the generator's predicate.

**Definitional disagreement (kappa 0.2 to 0.5): `unauthorized_scope`, `financial_commitment`,
`destructive_or_irreversible_action`, `suspicious_action_sequence`, `external_communication`,
`untrusted_destination`.** The judge and the generator use different definitions, and the
rationales say which. `unauthorized_scope`: the judge flags twice as many rows as the
generator (159 vs 81) because it treats a mismatch with the stated objective ("bulk
retrieval of 279 records exceeds a single-record lookup") as out of scope, while the
generator's label is entitlement-based only. `financial_commitment`: the judge requires
funds to move; the generator labels any call carrying a financial amount. `external_communication`
and `suspicious_action_sequence`: the judge is more liberal (precision 0.23 and 0.33). These
are taxonomy decisions, not data defects. Each one needs a sentence in the dimension
definition saying which reading is intended, and the generator's predicate and the judge
prompt then have to agree.

**Not recoverable (kappa below 0.1): `insufficient_context`, `sensitive_data_exposure`.**
For `insufficient_context` the judge says the context is sufficient on 50 of the 58
generator-yes rows; the generator's notion of a context gap is not visible in the rendered
text. For `sensitive_data_exposure` the judge requires a transfer to a lower-sensitivity
sink and the generator labels reads of confidential data through an authorised tool as
exposure; recall 0.17, precision 0.08.

## Consequences for the results elsewhere

- The identity-ablation claim rests on `unauthorized_scope` (kappa 0.39), `policy_conflict`
  (0.71) and `insufficient_context` (0.06). `policy_conflict` is solid. `unauthorized_scope`
  is directionally confirmed (judge recall 0.74 of generator positives) but the two
  definitions differ. `insufficient_context` is the weak leg: the trained model scores 0.84
  AUPRC on a label a blind frontier reader cannot recover, which means the model is likely
  reading a generator regularity rather than a fact about the text. Treat the
  `insufficient_context` numbers as unvalidated until the generator makes the gap explicit
  in the rendering or the definition changes.
- `sensitive_data_exposure` is a lookup dimension for the rule baseline (1.0) and the model;
  the judge result says the label encodes a definition ("confidential data touched") that a
  reader would not call exposure. Rename or redefine before reporting it as a risk detector.
- The content dimensions that survive identity stripping (`prompt_injection_influence`,
  `privilege_escalation`) are exactly the ones the judge recovers best, which is consistent
  with them being properties of the text.

## Judge without identity context (`v4-labels-gpt56-noid.jsonl`, `agreement-gpt56-noid/`)

Same 600 stratified v4 rows, same judge (gpt-5.6-sol), same method, but the rendered
context has principal entitlements, agent delegated scopes, the delegation chain and
policy text removed before judging -- the same `--strip-identity` rendering used for the
model identity ablation. 600/600 rows labelled, 6 needed a retry, 0 provider errors
after the retry pass.

Yes-vs-not-yes Cohen's kappa against the generator label, full-context pass vs stripped
pass, n=600 each:

| dimension | kappa full | kappa stripped | judge yes full | judge yes stripped | recall full | recall stripped | precision full | precision stripped |
|---|---|---|---|---|---|---|---|---|
| privilege_escalation | 0.909 | 0.909 | 45 | 45 | 1.00 | 1.00 | 0.84 | 0.84 |
| prompt_injection_influence | 0.905 | 0.905 | 53 | 53 | 0.84 | 0.84 | 1.00 | 1.00 |
| policy_conflict | 0.714 | 0.029 | 259 | 28 | 0.89 | 0.06 | 0.78 | 0.50 |
| destructive_or_irreversible_action | 0.511 | 0.542 | 76 | 73 | 0.60 | 0.62 | 0.54 | 0.58 |
| suspicious_action_sequence | 0.404 | 0.428 | 120 | 121 | 0.82 | 0.86 | 0.33 | 0.35 |
| unauthorized_scope | 0.391 | 0.040 | 159 | 203 | 0.74 | 0.40 | 0.38 | 0.16 |
| financial_commitment | 0.359 | 0.300 | 13 | 12 | 0.24 | 0.20 | 0.92 | 0.83 |
| external_communication | 0.331 | 0.361 | 77 | 80 | 0.86 | 0.95 | 0.23 | 0.25 |
| untrusted_destination | 0.213 | 0.205 | 119 | 113 | 0.41 | 0.39 | 0.29 | 0.29 |
| insufficient_context | 0.059 | -0.036 | 52 | 219 | 0.14 | 0.29 | 0.15 | 0.08 |
| sensitive_data_exposure | 0.002 | 0.061 | 98 | 109 | 0.17 | 0.27 | 0.08 | 0.12 |

Generator yes counts are identical across both passes, same 600 rows and the same
generator labels: privilege_escalation 38, prompt_injection_influence 63, policy_conflict
228, destructive_or_irreversible_action 68, suspicious_action_sequence 49,
unauthorized_scope 81, financial_commitment 50, external_communication 21,
untrusted_destination 85, insufficient_context 58, sensitive_data_exposure 48.

**Reading.** Stripping identity context from the text removes the judge's ability to
recover exactly the two dimensions the model identity ablation says depend on identity.
`policy_conflict` falls from kappa 0.714 to 0.029: the judge finds 28 positives instead
of 259 because the policy text it would check the action against is no longer there.
`unauthorized_scope` falls from 0.391 to 0.040: the judge now flags 203 rows at precision
0.16, which means it is guessing from the action alone rather than reading an
entitlement. Every other dimension is unchanged within noise; the largest other move is
`destructive_or_irreversible_action`, 0.511 to 0.542.

This is an independent replication of the identity-ablation result on labels rather than
on model scores. A blind frontier reader loses the same two dimensions the trained
checker loses when identity is stripped (`unauthorized_scope` 0.999 to 0.125 AUPRC,
`policy_conflict` 0.964 to 0.392 AUPRC, identity section of
`docs/results/synthetic-v2/README.md`), and keeps the same content dimensions
(`prompt_injection_influence`, `privilege_escalation`) the checker keeps.
`insufficient_context` is unrecoverable in both passes (kappa 0.059 full, -0.036
stripped), which is the third leg of the identity claim and stays unvalidated. The
content dimensions did not move at all between passes -- identical judge-yes and
generator-yes counts -- which also confirms that stripping identity did not alter the
tool-call or trajectory text itself.

## Next

1. Tighten the six definitional dimensions in `src/forecheck/judge/dimensions.py` and the
   generator's `labeling.py` so they state the same reading, then re-judge.

## Model scored against judge labels (`model-vs-judge/`, job `eval-v4-judge`)

`forecheck evaluate --labels-from v4-labels-gpt56.jsonl` on the trained 2B v4 checker and
the rule baseline, restricted to the judged rows (n = 257 heldout_family, 95
heldout_policy_kind, 248 test). Small n, so read the ordering, not the third decimal.

| dimension | model, heldout_family | rule, heldout_family | model, heldout_policy_kind | model, test | model vs generator labels (heldout_family) |
|---|---|---|---|---|---|
| prompt_injection_influence | 1.000 | 0.459 | 1.000 | 1.000 | 0.804 |
| privilege_escalation | 0.977 | 0.297 | 1.000 | 0.818 | 1.000 |
| policy_conflict | 0.889 | 0.502 | 0.772 | 0.804 | 0.964 |
| untrusted_destination | 0.864 | 0.785 | 0.863 | 0.825 | 1.000 |
| destructive_or_irreversible_action | 0.635 | 0.509 | 0.071 | 0.377 | 0.992 |
| unauthorized_scope | 0.592 | 0.509 | 0.711 | 0.572 | 0.999 |
| suspicious_action_sequence | 0.528 | 0.467 | 0.417 | 0.526 | 0.966 |
| external_communication | 0.437 | 0.381 | 0.197 | 0.181 | 1.000 |
| sensitive_data_exposure | 0.405 | 0.291 | 0.116 | 0.144 | 1.000 |
| financial_commitment | 0.327 | 0.280 | 0.450 | 0.179 | 1.000 |
| insufficient_context | 0.090 | 0.090 | 0.181 | 0.079 | 0.841 |
| macro | 0.613 | 0.415 | 0.525 | 0.500 | 0.960 |

Reading. Against labels the generator did not write, the model keeps the three
recoverable dimensions (`prompt_injection_influence` 1.00, `privilege_escalation` 0.98,
`policy_conflict` 0.89) and `untrusted_destination` (0.86), and beats the rule baseline on
every one of them by 0.08 to 0.68. `unauthorized_scope` falls to 0.59 because the judge's
definition (objective mismatch) differs from the trained one (entitlements); this is the
same definitional gap as the kappa of 0.39 above, not a model failure, and it is fixed by
choosing one definition. `insufficient_context` at 0.09 confirms the label is a generator
artefact: the model's 0.84 against generator labels is not a fact about the text. The
lookup dimensions (`financial_commitment`, `external_communication`,
`sensitive_data_exposure`) collapse because the judge and generator define them
differently, and the rule baseline collapses with them.

The number to carry into the paper: on labels from an independent blind reader the
learned checker scores 0.61 macro against 0.42 for rules on heldout_family, with the gap
concentrated in the dimensions that need reading (injection, policy, authority change),
and `insufficient_context` should be dropped from any headline claim.
