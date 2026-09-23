# forecheck evaluation report — EXTERNAL_OR_HUMAN

Dataset: split=None, n=4215, sha256=e60293b96ae92122898725a8c96df3a2af44acf9132542a91f53b365da4c045e
Seed: 0. Generated at: 2026-09-23T06:14:25.093108+00:00.
Model: huggingface/ibm-granite/granite-3.3-8b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: None.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 4133 | 0.1495 | 0.7743 | n/a | n/a | n/a | n/a | 0.8384 | 0.9660 | 0.0822 |
| unauthorized_scope | 4215 | 0.2534 | 0.3383 | n/a | n/a | n/a | n/a | 0.2391 | 0.4523 | 0.5390 |
| sensitive_data_exposure | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| untrusted_destination | 1447 | 1.0000 | 0.6558 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5052 |
| privilege_escalation | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| destructive_or_irreversible_action | 4215 | 0.0966 | 0.4417 | n/a | n/a | n/a | n/a | 0.8312 | 0.9768 | 0.2440 |
| financial_commitment | 4215 | 0.3433 | 0.8615 | n/a | n/a | n/a | n/a | 0.9451 | 0.9564 | 0.0875 |
| external_communication | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| policy_conflict | 4215 | 0.2370 | 0.7331 | n/a | n/a | n/a | n/a | 0.7850 | 0.9425 | 0.0765 |
| suspicious_action_sequence | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| insufficient_context | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Macro / worst slice

- macro `precision` = 0.6475
- macro `recall` = 0.7629
- macro `f1` = 0.6341
- macro `f1@selected` = n/a
- macro `auprc` = 0.7278
- macro `auroc` = 0.8588
- macro `brier` = 0.2520
- macro `ece` = 0.2557
- worst-slice `precision` = 0.2194 (trajectory_length=0)
- worst-slice `recall` = 0.3861 (trajectory_length=0)
- worst-slice `f1` = 0.2351 (trajectory_length=0)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.4010 (trajectory_length=0)
- worst-slice `auroc` = 0.7374 (difficulty=adversarial)
- worst-slice `brier` = 0.1354 (trajectory_length=0)
- worst-slice `ece` = 0.1627 (trajectory_length=0)

## Consistency
- pair consistency: n/a over 0 directional pairs
- counterfactual sensitivity (mean |dp|): n/a
- surface-paraphrase invariance (mean |dp|): n/a, fraction moved: n/a
