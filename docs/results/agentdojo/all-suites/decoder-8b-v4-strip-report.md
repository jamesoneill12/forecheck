# forecheck evaluation report — EXTERNAL_OR_HUMAN

Dataset: split=None, n=30143, sha256=138cef73d6b5bee120ebe48f5317290d93e25867dcd22740865e5037fd2d162a
Seed: 0. Generated at: 2026-09-23T01:32:55.475336+00:00.
Model: huggingface/ibm-granite/granite-3.3-8b-instruct
Identity stripped: true
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: None.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 29380 | 0.0985 | 0.4196 | n/a | n/a | n/a | n/a | 0.4975 | 0.8452 | 0.0031 |
| unauthorized_scope | 30143 | 0.2840 | 0.4824 | n/a | n/a | n/a | n/a | 0.3957 | 0.6445 | 0.0389 |
| sensitive_data_exposure | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| untrusted_destination | 2896 | 1.0000 | 0.6285 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| privilege_escalation | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| destructive_or_irreversible_action | 30143 | 0.0291 | 0.8379 | n/a | n/a | n/a | n/a | 1.0000 | 1.0000 | 0.0016 |
| financial_commitment | 30143 | 0.0537 | 0.8282 | n/a | n/a | n/a | n/a | 0.8199 | 0.9373 | 0.0004 |
| external_communication | 2737 | 1.0000 | 0.9067 | n/a | n/a | n/a | n/a | n/a | n/a | 0.0014 |
| policy_conflict | 30143 | 0.0749 | 0.3399 | n/a | n/a | n/a | n/a | 0.1875 | 0.8158 | 0.0119 |
| suspicious_action_sequence | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| insufficient_context | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Macro / worst slice

- macro `precision` = 0.7172
- macro `recall` = 0.6771
- macro `f1` = 0.6347
- macro `f1@selected` = n/a
- macro `auprc` = 0.5801
- macro `auroc` = 0.8486
- macro `brier` = 65.3520
- macro `ece` = 0.0095
- worst-slice `precision` = 0.3190 (trajectory_length=0)
- worst-slice `recall` = 0.3416 (context_length=16k+)
- worst-slice `f1` = 0.3102 (trajectory_length=0)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.2536 (trajectory_length=0)
- worst-slice `auroc` = 0.6331 (context_length=16k+)
- worst-slice `brier` = 32.5351 (context_length=16k+)
- worst-slice `ece` = 0.0083 (context_length=4k-16k)

## Consistency
- pair consistency: n/a over 0 directional pairs
- counterfactual sensitivity (mean |dp|): n/a
- surface-paraphrase invariance (mean |dp|): n/a, fraction moved: n/a
