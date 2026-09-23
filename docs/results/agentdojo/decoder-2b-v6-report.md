# forecheck evaluation report — EXTERNAL_OR_HUMAN

Dataset: split=None, n=4215, sha256=e60293b96ae92122898725a8c96df3a2af44acf9132542a91f53b365da4c045e
Seed: 0. Generated at: 2026-09-23T04:17:05.319231+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: None.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 4133 | 0.1495 | 0.5683 | n/a | n/a | n/a | n/a | 0.6931 | 0.9280 | 0.1865 |
| unauthorized_scope | 4215 | 0.2534 | 0.3114 | n/a | n/a | n/a | n/a | 0.2138 | 0.3562 | 0.6291 |
| sensitive_data_exposure | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| untrusted_destination | 1447 | 1.0000 | 0.6558 | n/a | n/a | n/a | n/a | n/a | n/a | 0.4933 |
| privilege_escalation | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| destructive_or_irreversible_action | 4215 | 0.0966 | 0.7172 | n/a | n/a | n/a | n/a | 1.0000 | 1.0000 | 0.0830 |
| financial_commitment | 4215 | 0.3433 | 0.9141 | n/a | n/a | n/a | n/a | 0.9348 | 0.9338 | 0.0543 |
| external_communication | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| policy_conflict | 4215 | 0.2370 | 0.4065 | n/a | n/a | n/a | n/a | 0.6704 | 0.9045 | 0.1113 |
| suspicious_action_sequence | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| insufficient_context | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Macro / worst slice

- macro `precision` = 0.6346
- macro `recall` = 0.7091
- macro `f1` = 0.5956
- macro `f1@selected` = n/a
- macro `auprc` = 0.7024
- macro `auroc` = 0.8245
- macro `brier` = 0.2477
- macro `ece` = 0.2596
- worst-slice `precision` = 0.2148 (trajectory_length=0)
- worst-slice `recall` = 0.3569 (trajectory_length=0)
- worst-slice `f1` = 0.2270 (trajectory_length=0)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.3651 (trajectory_length=0)
- worst-slice `auroc` = 0.6969 (difficulty=adversarial)
- worst-slice `brier` = 0.1243 (trajectory_length=0)
- worst-slice `ece` = 0.1560 (trajectory_length=0)

## Consistency
- pair consistency: n/a over 0 directional pairs
- counterfactual sensitivity (mean |dp|): n/a
- surface-paraphrase invariance (mean |dp|): n/a, fraction moved: n/a
