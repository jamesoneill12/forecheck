# forecheck evaluation report — EXTERNAL_OR_HUMAN

Dataset: split=None, n=4215, sha256=e60293b96ae92122898725a8c96df3a2af44acf9132542a91f53b365da4c045e
Seed: 0. Generated at: 2026-09-25T11:55:58.701650+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: None.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 4133 | 0.1495 | 0.4857 | n/a | n/a | n/a | n/a | 0.3538 | 0.8027 | 0.2106 |
| unauthorized_scope | 4215 | 0.2534 | 0.0000 | n/a | n/a | n/a | n/a | 0.2199 | 0.3516 | 0.2401 |
| sensitive_data_exposure | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| untrusted_destination | 1447 | 1.0000 | 0.6558 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5112 |
| privilege_escalation | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| destructive_or_irreversible_action | 4215 | 0.0966 | 0.4417 | n/a | n/a | n/a | n/a | 0.9935 | 0.9995 | 0.2406 |
| financial_commitment | 4215 | 0.3433 | 1.0000 | n/a | n/a | n/a | n/a | 1.0000 | 1.0000 | 0.0000 |
| external_communication | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| policy_conflict | 4215 | 0.2370 | 0.0000 | n/a | n/a | n/a | n/a | 0.2982 | 0.6441 | 0.1992 |
| suspicious_action_sequence | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| insufficient_context | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Macro / worst slice

- macro `precision` = 0.4372
- macro `recall` = 0.5565
- macro `f1` = 0.4305
- macro `f1@selected` = n/a
- macro `auprc` = 0.5731
- macro `auroc` = 0.7596
- macro `brier` = 0.2356
- macro `ece` = 0.2336
- worst-slice `precision` = 0.2000 (trajectory_length=0)
- worst-slice `recall` = 0.2000 (trajectory_length=0)
- worst-slice `f1` = 0.2000 (trajectory_length=0)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.5036 (context_length=<1k)
- worst-slice `auroc` = 0.7042 (difficulty=adversarial)
- worst-slice `brier` = 0.0192 (trajectory_length=0)
- worst-slice `ece` = 0.0332 (trajectory_length=0)

## Consistency
- pair consistency: n/a over 0 directional pairs
- counterfactual sensitivity (mean |dp|): n/a
- surface-paraphrase invariance (mean |dp|): n/a, fraction moved: n/a
