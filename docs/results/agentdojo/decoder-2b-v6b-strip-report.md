# forecheck evaluation report — EXTERNAL_OR_HUMAN

Dataset: split=None, n=4215, sha256=e60293b96ae92122898725a8c96df3a2af44acf9132542a91f53b365da4c045e
Seed: 0. Generated at: 2026-09-25T01:06:39.237647+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: true
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: None.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 4133 | 0.1495 | 0.0908 | n/a | n/a | n/a | n/a | 0.1346 | 0.2935 | 0.0000 |
| unauthorized_scope | 4215 | 0.2534 | 0.4043 | n/a | n/a | n/a | n/a | 0.2205 | 0.4111 | n/a |
| sensitive_data_exposure | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| untrusted_destination | 1447 | 1.0000 | 0.6558 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| privilege_escalation | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| destructive_or_irreversible_action | 4215 | 0.0966 | 0.4708 | n/a | n/a | n/a | n/a | 1.0000 | 1.0000 | 0.0002 |
| financial_commitment | 4215 | 0.3433 | 0.9407 | n/a | n/a | n/a | n/a | 1.0000 | 1.0000 | 0.0156 |
| external_communication | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| policy_conflict | 4215 | 0.2370 | 0.2211 | n/a | n/a | n/a | n/a | 0.2714 | 0.5499 | 0.0548 |
| suspicious_action_sequence | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| insufficient_context | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Macro / worst slice

- macro `precision` = 0.4950
- macro `recall` = 0.6058
- macro `f1` = 0.4639
- macro `f1@selected` = n/a
- macro `auprc` = 0.5253
- macro `auroc` = 0.6509
- macro `brier` = 115.5659
- macro `ece` = 0.0177
- worst-slice `precision` = 0.2168 (trajectory_length=0)
- worst-slice `recall` = 0.4000 (trajectory_length=0)
- worst-slice `f1` = 0.2311 (trajectory_length=0)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.3734 (trajectory_length=0)
- worst-slice `auroc` = 0.6509 (tool_family=payments_procurement)
- worst-slice `brier` = 55.5578 (difficulty=adversarial)
- worst-slice `ece` = 0.0177 (tool_family=payments_procurement)

## Consistency
- pair consistency: n/a over 0 directional pairs
- counterfactual sensitivity (mean |dp|): n/a
- surface-paraphrase invariance (mean |dp|): n/a, fraction moved: n/a
