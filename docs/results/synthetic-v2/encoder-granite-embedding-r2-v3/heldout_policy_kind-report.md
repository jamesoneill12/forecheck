# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_policy_kind, n=2247, sha256=d5b55de7ffe2bc91894ffe5395c035382a5987a63a61344ca57a03119e530f56
Seed: 0. Generated at: 2026-09-21T23:23:51.706175+00:00.
Model: encoder/ibm-granite/granite-embedding-english-r2
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_policy_kind.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 2247 | 0.0757 | 0.7893 | 0.9963 | 1.0000 | 0.6824 | 0.8112 | 0.7460 | 0.8525 | 0.0177 |
| unauthorized_scope | 2139 | 0.1169 | 0.9861 | 0.5876 | 0.9802 | 0.9920 | 0.9861 | 0.9987 | 0.9998 | 0.0052 |
| sensitive_data_exposure | 510 | 0.2118 | 0.9908 | 0.7769 | 0.9907 | 0.9907 | 0.9907 | 0.9998 | 1.0000 | 0.0150 |
| untrusted_destination | 647 | 0.3215 | 0.9904 | 0.7567 | 0.9856 | 0.9856 | 0.9856 | 0.9961 | 0.9967 | 0.0135 |
| privilege_escalation | 2247 | 0.0191 | 0.6043 | 0.7905 | 0.4651 | 0.9302 | 0.6202 | 0.5861 | 0.9907 | 0.0374 |
| destructive_or_irreversible_action | 2247 | 0.0961 | 0.9860 | 0.8861 | 0.9953 | 0.9722 | 0.9836 | 0.9970 | 0.9996 | 0.0050 |
| financial_commitment | 2247 | 0.0797 | 1.0000 | 0.9173 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0021 |
| external_communication | 53 | 0.6226 | 0.9851 | 0.5137 | 0.9706 | 1.0000 | 0.9851 | 1.0000 | 1.0000 | 0.0908 |
| policy_conflict | 2247 | 0.4050 | 0.4405 | 0.3797 | 0.4050 | 1.0000 | 0.5765 | 0.4420 | 0.5542 | 0.0885 |
| suspicious_action_sequence | 460 | 0.3130 | 0.7586 | 0.5983 | 0.8189 | 0.7222 | 0.7675 | 0.8532 | 0.8951 | 0.0788 |
| insufficient_context | 2247 | 0.0788 | 0.6328 | 0.7384 | 0.5735 | 0.8814 | 0.6949 | 0.7063 | 0.9611 | 0.1560 |

## Macro / worst slice

- macro `precision` = 0.8127
- macro `recall` = 0.8871
- macro `f1` = 0.8331
- macro `f1@selected` = 0.8547
- macro `auprc` = 0.8477
- macro `auroc` = 0.9318
- macro `brier` = 0.0486
- macro `ece` = 0.0464
- worst-slice `precision` = 0.1111 (contrastive_axis=permission_versus_escalation)
- worst-slice `recall` = 0.1111 (contrastive_axis=permission_versus_escalation)
- worst-slice `f1` = 0.1111 (contrastive_axis=permission_versus_escalation)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.6827 (contrastive_axis=principal_authorization)
- worst-slice `auroc` = 0.7417 (contrastive_axis=reversibility)
- worst-slice `brier` = 0.0325 (contrastive_axis=environment_stage)
- worst-slice `ece` = 0.0409 (tool_family=file_storage)

## Consistency
- pair consistency: 0.9677 over 31 directional pairs
- counterfactual sensitivity (mean |dp|): 0.7985
- surface-paraphrase invariance (mean |dp|): 0.0383, fraction moved: 1.0000
