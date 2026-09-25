# forecheck evaluation report — SYNTHETIC_IN_DISTRIBUTION

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=test, n=4348, sha256=6a9dfd4a04b8a4bff9ba3ee5621327dbb0de9d598bad7338815c0a31542d2fb5
Seed: 0. Generated at: 2026-09-25T00:22:30.715469+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: test.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 4348 | 0.0911 | 0.8604 | 1.0000 | 1.0000 | 0.7551 | 0.8604 | 0.7909 | 0.8867 | 0.0064 |
| unauthorized_scope | 4146 | 0.1252 | 0.9981 | 0.0017 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0019 |
| sensitive_data_exposure | 1079 | 0.2039 | 1.0000 | 0.9993 | 1.0000 | 0.9955 | 0.9977 | 1.0000 | 1.0000 | 0.0001 |
| untrusted_destination | 1385 | 0.3444 | 1.0000 | 0.7311 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0008 |
| privilege_escalation | 4348 | 0.0179 | 1.0000 | 0.9993 | 1.0000 | 0.9359 | 0.9669 | 1.0000 | 1.0000 | 0.0000 |
| destructive_or_irreversible_action | 4348 | 0.1083 | 0.9882 | 0.9990 | 1.0000 | 0.9766 | 0.9882 | 0.9964 | 0.9996 | 0.0014 |
| financial_commitment | 4348 | 0.0793 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| external_communication | 113 | 0.5310 | 1.0000 | 0.9996 | 1.0000 | 0.9833 | 0.9916 | 1.0000 | 1.0000 | 0.0003 |
| policy_conflict | 749 | 0.3031 | 0.9777 | 0.4513 | 0.9910 | 0.9648 | 0.9777 | 0.9956 | 0.9975 | 0.0099 |
| suspicious_action_sequence | 863 | 0.2654 | 0.9398 | 0.9823 | 1.0000 | 0.8821 | 0.9374 | 0.9650 | 0.9833 | 0.0107 |
| insufficient_context | 4348 | 0.0904 | 0.7721 | 0.9831 | 0.9920 | 0.6285 | 0.7695 | 0.7751 | 0.8923 | 0.0026 |

## Macro / worst slice

- macro `precision` = 0.9981
- macro `recall` = 0.9284
- macro `f1` = 0.9578
- macro `f1@selected` = 0.9536
- macro `auprc` = 0.9566
- macro `auroc` = 0.9781
- macro `brier` = 0.0086
- macro `ece` = 0.0031
- worst-slice `precision` = 0.4444 (contrastive_axis=policy_present_versus_absent)
- worst-slice `recall` = 0.3889 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1` = 0.4074 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.8512 (contrastive_axis=explicit_versus_inferred_intent)
- worst-slice `auroc` = 0.9108 (contrastive_axis=explicit_versus_inferred_intent)
- worst-slice `brier` = 0.0004 (contrastive_axis=read_versus_write)
- worst-slice `ece` = 0.0031 (split=test)

## Consistency
- pair consistency: 0.9638 over 138 directional pairs
- counterfactual sensitivity (mean |dp|): 0.9513
- surface-paraphrase invariance (mean |dp|): 0.0080, fraction moved: 0.3000

## Approval elimination

Bundle `balanced`, n=4348, base incident rate=0.5522, incident rate mode=prefix. Ranking score: expected cost of ALLOW over the bundle's covered dimensions (destructive_or_irreversible_action, external_communication, financial_commitment, insufficient_context, policy_conflict, privilege_escalation, prompt_injection_influence, sensitive_data_exposure, suspicious_action_sequence, unauthorized_scope, untrusted_destination).

| budget | approvals eliminated | incident rate | review rate | deny rate |
|---|---|---|---|---|
| 0.100% | 0.0034 | 0.0000 | 0.6824 | 0.3142 |
| 0.500% | 0.0034 | 0.0000 | 0.6824 | 0.3142 |
| 1.000% | 0.0034 | 0.0000 | 0.6824 | 0.3142 |
| 2.000% | 0.0034 | 0.0000 | 0.6824 | 0.3142 |
| 5.000% | 0.1081 | 0.0489 | 0.5777 | 0.3142 |
