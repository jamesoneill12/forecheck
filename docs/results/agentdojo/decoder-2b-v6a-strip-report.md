# forecheck evaluation report — EXTERNAL_OR_HUMAN

Dataset: split=None, n=4215, sha256=e60293b96ae92122898725a8c96df3a2af44acf9132542a91f53b365da4c045e
Seed: 0. Generated at: 2026-09-25T00:47:15.417647+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: true
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: None.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 4133 | 0.1495 | 0.6488 | n/a | n/a | n/a | n/a | 0.6641 | 0.9308 | 0.0139 |
| unauthorized_scope | 4215 | 0.2534 | 0.4043 | n/a | n/a | n/a | n/a | 0.3640 | 0.6287 | 0.0008 |
| sensitive_data_exposure | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| untrusted_destination | 1447 | 1.0000 | 0.6558 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| privilege_escalation | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| destructive_or_irreversible_action | 4215 | 0.0966 | 0.4417 | n/a | n/a | n/a | n/a | 0.7412 | 0.9754 | n/a |
| financial_commitment | 4215 | 0.3433 | 0.9141 | n/a | n/a | n/a | n/a | 1.0000 | 1.0000 | n/a |
| external_communication | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| policy_conflict | 4215 | 0.2370 | 0.1073 | n/a | n/a | n/a | n/a | 0.3926 | 0.7794 | 0.0095 |
| suspicious_action_sequence | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| insufficient_context | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Macro / worst slice

- macro `precision` = 0.5586
- macro `recall` = 0.6877
- macro `f1` = 0.5287
- macro `f1@selected` = n/a
- macro `auprc` = 0.6324
- macro `auroc` = 0.8628
- macro `brier` = 104.0040
- macro `ece` = 0.0081
- worst-slice `precision` = 0.2168 (trajectory_length=0)
- worst-slice `recall` = 0.4000 (trajectory_length=0)
- worst-slice `f1` = 0.2311 (trajectory_length=0)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.4471 (trajectory_length=0)
- worst-slice `auroc` = 0.7898 (difficulty=adversarial)
- worst-slice `brier` = 51.4663 (context_length=4k-16k)
- worst-slice `ece` = 0.0006 (context_length=<1k)

## Consistency
- pair consistency: n/a over 0 directional pairs
- counterfactual sensitivity (mean |dp|): n/a
- surface-paraphrase invariance (mean |dp|): n/a, fraction moved: n/a
