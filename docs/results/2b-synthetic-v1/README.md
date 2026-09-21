# Run `2b-synthetic-v1` — first GPU training run

> Synthetic data throughout. No real-world safety claim is made. This run's main
> value was diagnostic: it exposed generator defects that the offline test suite could
> not, and those defects are fixed in the commits that follow it.

| | |
|---|---|
| Date | 2026-09-21 |
| Base model | `ibm-granite/granite-3.3-2b-instruct` (Apache-2.0), bf16, SDPA |
| Adapter | LoRA r16 / α32 / dropout 0.05 on q,k,v,o; LR 2e-4 cosine, warmup 3%, mbs 16 |
| Prompt contract | 1.3.0 (4-message chat layout, shared prefill on the role-header token) |
| Data | `configs/data/train_medium.yaml` @ commit `4fa9439`, 50,004 rows; train 30,319 / calibration 5,043 / dev 4,932 / test 4,955 / heldout_family 2,290 / adversarial 2,465 |
| Hardware | 1 × B200 (EKS `eks-fsdp-cluster`, job `jamesoneill-forecheck-train-2b-9972064f`) |
| Wall clock | train 68 min (early-stopped at step 2200 of 5,685; best step 1200), calibrate 57 min, evaluate 56 + 26 min |
| Artifacts | `test-report.md`, `heldout_family-report.md`, `calibration-bundle.json`, `metrics.jsonl` (this directory); checkpoints on FSx `/opt/ml/fsx/forecheck/runs/2b-synthetic-v1` |

## Headline numbers

| split | class | macro AUPRC | macro AUROC | macro F1@0.5 | macro ECE | macro Brier |
|---|---|---|---|---|---|---|
| test | synthetic_in_distribution | 0.820 | 0.935 | 0.761 | 0.0067 | 0.029 |
| heldout_family | synthetic_heldout_adversarial | 0.826 | 0.915 | 0.734 | 0.0112 | 0.029 |

Dev macro-AUPRC by step: 0.784 (200), 0.731 (400), 0.788, 0.807, 0.808, **0.813 (1200)**,
0.799, 0.803, 0.807, 0.811, 0.803 (2200). Train loss 0.32 → 0.06. Temperature scaling on
the calibration split moved macro ECE 0.0118 → 0.0052.

Per-dimension AUPRC (test / heldout_family):

| dimension | test | heldout | reading |
|---|---|---|---|
| unauthorized_scope | 1.000 | 1.000 | saturated |
| sensitive_data_exposure | 1.000 | 1.000 | saturated |
| untrusted_destination | 1.000 | 1.000 | saturated |
| financial_commitment | 1.000 | 1.000 | saturated |
| external_communication | 1.000 | n/a (0 evaluable) | saturated / no coverage |
| destructive_or_irreversible_action | 0.997 | 0.994 | saturated |
| policy_conflict | 0.999 | 0.998 | saturated |
| insufficient_context | 0.804 | 0.790 | learnable, room to improve |
| privilege_escalation | 0.467 (AUROC 0.985, F1@0.5 = 0) | n/a (0 positives) | threshold + coverage problems |
| prompt_injection_influence | 0.451 | 0.401 | label not observable in text |
| suspicious_action_sequence | 0.307 (AUROC 0.52) | 0.255 (AUROC 0.49) | chance: label not observable in text |

## What the run actually showed

The model is not the story here; the generator and evaluation harness are.

1. **`suspicious_action_sequence` was unlearnable by construction.** The label came
   from `latent.sequence_pattern`, but `_build_trajectory` emitted random same-family
   tools with `outcome=success, "Completed without error."` regardless of pattern, and
   the pattern itself was never serialised. Attack and benign trajectories rendered
   identically. Fixed in `6ec4d66`: per-pattern role schedules, tools resolved by
   `ToolSpec` tags, per-role outcome pools shared by attack and benign patterns.
2. **`prompt_injection_influence` depended on a hidden field.** `action_origin` drove
   the label but only `untrusted_content_contains_instruction` drove the text, so true
   positives and the deliberate hard negatives were byte-identical in style. Fixed in
   `6ec4d66`: injected instructions name a verb + target and the proposed action's
   arguments follow it only when `action_origin == INJECTED_INSTRUCTION`.
3. **`privilege_escalation` F1 = 0 was the fixed 0.5 threshold** on a 2.4%-positive
   class the model ranks well (AUROC 0.985). Fixed in `de4f1b5`: reports now carry
   precision/recall/F1 at the dev-selected F1-optimal threshold beside F1@0.5, and the
   CLI defaults `--threshold-split dev`.
4. **Consistency metrics were empty.** `pairs_per_axis` defaulted to 1 → 42 pairs in
   50k rows, 4 in test, 0 in heldout. Fixed in `6ec4d66`: default 40, `train_medium`
   130, and pair groups route through their own eval-heavy ratio table (≥25 pairs per
   axis in each of calibration/dev/test at 50k rows).
5. **Heldout coverage was luck.** Three tools withheld by plain hash, none performing
   `grant` → no `privilege_escalation` positives and no evaluable
   `external_communication` rows. Fixed in the commit that adds this file: heldout
   selection is stratified by `OperationKind` (10 of 72 tools withheld, at least one
   per operation); at 50k rows every dimension now has ≥55 positives in every eval split.
6. **Seven dimensions at AUPRC ≈ 1.0 are template lookup, not reasoning.** The
   serialiser prints the deciding structured field verbatim (`reversible=False`,
   `amount: 1200`, `relationship: unknown_external`). That is legitimate for a
   structured wire format, and production contexts will carry the same fields, but it
   means those dimensions do not test anything a rule could not do. The
   `rule_baseline` backend should be run on the same splits to quantify exactly that.
7. **Scoring throughput** was ~1.5 rows/s, CPU-bound on rendering the chat template
   twice per question. Fixed in `c75097e` (`ChatPrefillPlanner`); calibrate/evaluate
   should now take minutes.

## What this run does not tell us

- Anything about real-world agent tool calls. Every row is rendered by our own
  templates; heldout_family only tests unseen *tools* within our own distribution.
- Whether Granite-3.3-2B is the right base. The dimensions that were learnable are
  saturated and the ones that were not were unlearnable, so the base model's capacity
  was never the binding constraint.
- How this compares to alternatives. No baseline (rule engine, zero-shot frontier
  model, Nimble, open guard models) has been run on these splits yet.

## Next run (`2b-synthetic-v2`)

Same recipe on regenerated data with all fixes above. Expected changes: sequence and
injection dimensions move off chance; heldout privilege_escalation becomes evaluable;
consistency metrics populate; run time drops to ~1.5 h total. Then run `rule_baseline`
on the same splits, and only after that decide on the 8B / OLMo / encoder arms.
