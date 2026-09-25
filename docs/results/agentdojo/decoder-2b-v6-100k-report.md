# forecheck evaluation report — EXTERNAL_OR_HUMAN

Dataset: split=None, n=4215, sha256=e60293b96ae92122898725a8c96df3a2af44acf9132542a91f53b365da4c045e
Seed: 0. Generated at: 2026-09-25T09:08:53.986542+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: None.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 4133 | 0.1495 | 0.5431 | n/a | n/a | n/a | n/a | 0.4229 | 0.8588 | 0.2177 |
| unauthorized_scope | 4215 | 0.2534 | 0.3317 | n/a | n/a | n/a | n/a | 0.2702 | 0.4965 | 0.4198 |
| sensitive_data_exposure | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| untrusted_destination | 1447 | 1.0000 | 0.6558 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5121 |
| privilege_escalation | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| destructive_or_irreversible_action | 4215 | 0.0966 | 0.4417 | n/a | n/a | n/a | n/a | 1.0000 | 1.0000 | 0.2430 |
| financial_commitment | 4215 | 0.3433 | 1.0000 | n/a | n/a | n/a | n/a | 1.0000 | 1.0000 | 0.0000 |
| external_communication | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| policy_conflict | 4215 | 0.2370 | 0.7964 | n/a | n/a | n/a | n/a | 0.8504 | 0.9115 | 0.1342 |
| suspicious_action_sequence | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| insufficient_context | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Macro / worst slice

- macro `precision` = 0.6538
- macro `recall` = 0.7588
- macro `f1` = 0.6281
- macro `f1@selected` = n/a
- macro `auprc` = 0.7087
- macro `auroc` = 0.8534
- macro `brier` = 0.2439
- macro `ece` = 0.2545
- worst-slice `precision` = 0.2251 (trajectory_length=0)
- worst-slice `recall` = 0.3500 (trajectory_length=0)
- worst-slice `f1` = 0.2429 (trajectory_length=0)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.4026 (trajectory_length=0)
- worst-slice `auroc` = 0.7961 (trajectory_length=4-10)
- worst-slice `brier` = 0.0720 (trajectory_length=0)
- worst-slice `ece` = 0.0872 (trajectory_length=0)

## Consistency
- pair consistency: n/a over 0 directional pairs
- counterfactual sensitivity (mean |dp|): n/a
- surface-paraphrase invariance (mean |dp|): n/a, fraction moved: n/a
