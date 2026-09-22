# forecheck evaluation report — EXTERNAL_OR_HUMAN

Dataset: split=None, n=1000, sha256=e60293b96ae92122898725a8c96df3a2af44acf9132542a91f53b365da4c045e
Seed: 0. Generated at: 2026-09-22T21:06:31.978556+00:00.
Model: guardian_granite_guardian/ibm-granite/granite-guardian-3.3-8b
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: None.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 981 | 0.1549 | 0.0000 | n/a | n/a | n/a | n/a | 0.1030 | 0.2329 | 0.1169 |
| unauthorized_scope | 1000 | 0.2690 | 0.0000 | n/a | n/a | n/a | n/a | 0.2887 | 0.4943 | 0.1779 |
| sensitive_data_exposure | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| untrusted_destination | 357 | 1.0000 | 0.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 0.9186 |
| privilege_escalation | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| destructive_or_irreversible_action | 1000 | 0.0910 | 0.0000 | n/a | n/a | n/a | n/a | 0.2170 | 0.6974 | 0.0107 |
| financial_commitment | 1000 | 0.3570 | 0.0000 | n/a | n/a | n/a | n/a | 0.2567 | 0.2371 | 0.2692 |
| external_communication | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| policy_conflict | 1000 | 0.2460 | 0.0000 | n/a | n/a | n/a | n/a | 0.2240 | 0.4502 | 0.1585 |
| suspicious_action_sequence | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| insufficient_context | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Macro / worst slice

- macro `precision` = 0.0000
- macro `recall` = 0.0000
- macro `f1` = 0.0000
- macro `f1@selected` = n/a
- macro `auprc` = 0.2179
- macro `auroc` = 0.4224
- macro `brier` = 0.3016
- macro `ece` = 0.2753
- worst-slice `precision` = 0.0000 (tool_family=payments_procurement)
- worst-slice `recall` = 0.0000 (tool_family=payments_procurement)
- worst-slice `f1` = 0.0000 (tool_family=payments_procurement)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.0485 (context_length=<1k)
- worst-slice `auroc` = 0.4028 (trajectory_length=0)
- worst-slice `brier` = 0.0310 (trajectory_length=0)
- worst-slice `ece` = 0.0680 (context_length=<1k)

## Consistency
- pair consistency: n/a over 0 directional pairs
- counterfactual sensitivity (mean |dp|): n/a
- surface-paraphrase invariance (mean |dp|): n/a, fraction moved: n/a
