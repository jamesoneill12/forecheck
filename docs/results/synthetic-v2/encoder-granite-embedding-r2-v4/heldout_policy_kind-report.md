# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_policy_kind, n=2247, sha256=99c768cce2dd5ac344288cf1ca35a2825ca52a9ea3002ff39d94f71c96406a2c
Seed: 0. Generated at: 2026-09-22T10:56:16.892394+00:00.
Model: encoder/ibm-granite/granite-embedding-english-r2
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_policy_kind.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 2247 | 0.0757 | 0.7789 | 0.9616 | 0.9915 | 0.6824 | 0.8084 | 0.7437 | 0.8442 | 0.0249 |
| unauthorized_scope | 2139 | 0.1169 | 0.9920 | 0.6378 | 0.9960 | 0.9920 | 0.9940 | 0.9995 | 0.9999 | 0.0028 |
| sensitive_data_exposure | 510 | 0.2118 | 0.9683 | 0.7762 | 1.0000 | 0.9630 | 0.9811 | 0.9993 | 0.9998 | 0.0146 |
| untrusted_destination | 647 | 0.3215 | 0.9881 | 0.7960 | 0.9952 | 0.9904 | 0.9928 | 0.9970 | 0.9965 | 0.0108 |
| privilege_escalation | 2247 | 0.0191 | 0.6143 | 0.8238 | 0.4651 | 0.9302 | 0.6202 | 0.5756 | 0.9901 | 0.0385 |
| destructive_or_irreversible_action | 2247 | 0.0961 | 0.9746 | 0.8757 | 0.9857 | 0.9583 | 0.9718 | 0.9957 | 0.9995 | 0.0074 |
| financial_commitment | 2247 | 0.0797 | 1.0000 | 0.8233 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0021 |
| external_communication | 53 | 0.6226 | 1.0000 | 0.9863 | 1.0000 | 0.9697 | 0.9846 | 1.0000 | 1.0000 | 0.0119 |
| policy_conflict | 2247 | 0.4050 | 0.4759 | 0.4845 | 0.4064 | 0.9879 | 0.5759 | 0.4384 | 0.5451 | 0.0957 |
| suspicious_action_sequence | 460 | 0.3130 | 0.7010 | 0.6189 | 0.7913 | 0.6319 | 0.7027 | 0.8087 | 0.8522 | 0.0920 |
| insufficient_context | 2247 | 0.0788 | 0.6180 | 0.7596 | 0.5929 | 0.8475 | 0.6977 | 0.7351 | 0.9606 | 0.1525 |

## Macro / worst slice

- macro `precision` = 0.8014
- macro `recall` = 0.8908
- macro `f1` = 0.8283
- macro `f1@selected` = 0.8481
- macro `auprc` = 0.8448
- macro `auroc` = 0.9262
- macro `brier` = 0.0490
- macro `ece` = 0.0412
- worst-slice `precision` = 0.1429 (contrastive_axis=resource_sensitivity)
- worst-slice `recall` = 0.1429 (contrastive_axis=resource_sensitivity)
- worst-slice `f1` = 0.1429 (contrastive_axis=resource_sensitivity)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.6792 (contrastive_axis=principal_authorization)
- worst-slice `auroc` = 0.7600 (contrastive_axis=principal_authorization)
- worst-slice `brier` = 0.0370 (contrastive_axis=resource_sensitivity)
- worst-slice `ece` = 0.0364 (trajectory_length=0)

## Consistency
- pair consistency: 0.9677 over 31 directional pairs
- counterfactual sensitivity (mean |dp|): 0.8583
- surface-paraphrase invariance (mean |dp|): 0.0446, fraction moved: 1.0000
