# forecheck evaluation report — SYNTHETIC_IN_DISTRIBUTION

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=test, n=4412, sha256=3aa19ec814b3defba069f72d0152bd73422e09930e1d42f3ad51bf8390728d60
Seed: 0. Generated at: 2026-09-22T10:54:36.922361+00:00.
Model: encoder/ibm-granite/granite-embedding-english-r2
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: test.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 4412 | 0.0882 | 0.8305 | 0.9616 | 0.9966 | 0.7481 | 0.8546 | 0.8000 | 0.8625 | 0.0179 |
| unauthorized_scope | 4216 | 0.1191 | 0.9940 | 0.6378 | 0.9901 | 0.9960 | 0.9930 | 0.9997 | 1.0000 | 0.0026 |
| sensitive_data_exposure | 1073 | 0.2144 | 0.9722 | 0.7762 | 0.9868 | 0.9739 | 0.9803 | 0.9985 | 0.9996 | 0.0141 |
| untrusted_destination | 1367 | 0.3555 | 0.9855 | 0.7960 | 0.9979 | 0.9774 | 0.9875 | 0.9892 | 0.9865 | 0.0092 |
| privilege_escalation | 4412 | 0.0161 | 0.5569 | 0.8238 | 0.3865 | 0.8873 | 0.5385 | 0.4475 | 0.9886 | 0.0399 |
| destructive_or_irreversible_action | 4412 | 0.1145 | 0.9732 | 0.8757 | 0.9959 | 0.9505 | 0.9726 | 0.9934 | 0.9988 | 0.0041 |
| financial_commitment | 4412 | 0.0780 | 1.0000 | 0.8233 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0019 |
| external_communication | 95 | 0.5368 | 1.0000 | 0.9863 | 1.0000 | 0.9804 | 0.9901 | 1.0000 | 1.0000 | 0.0036 |
| policy_conflict | 752 | 0.3590 | 0.4963 | 0.4845 | 0.3558 | 0.9778 | 0.5217 | 0.4415 | 0.5829 | 0.1424 |
| suspicious_action_sequence | 904 | 0.3208 | 0.7744 | 0.6189 | 0.8400 | 0.7241 | 0.7778 | 0.8771 | 0.9121 | 0.0822 |
| insufficient_context | 4412 | 0.0857 | 0.5623 | 0.7596 | 0.5412 | 0.7302 | 0.6216 | 0.6310 | 0.8886 | 0.1387 |

## Macro / worst slice

- macro `precision` = 0.8037
- macro `recall` = 0.8966
- macro `f1` = 0.8314
- macro `f1@selected` = 0.8398
- macro `auprc` = 0.8344
- macro `auroc` = 0.9290
- macro `brier` = 0.0478
- macro `ece` = 0.0415
- worst-slice `precision` = 0.4000 (contrastive_axis=policy_present_versus_absent)
- worst-slice `recall` = 0.4000 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1` = 0.4000 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.7633 (difficulty=easy)
- worst-slice `auroc` = 0.8176 (contrastive_axis=destination_tenancy)
- worst-slice `brier` = 0.0274 (contrastive_axis=policy_present_versus_absent)
- worst-slice `ece` = 0.0380 (trajectory_length=0)

## Consistency
- pair consistency: 0.9686 over 159 directional pairs
- counterfactual sensitivity (mean |dp|): 0.8973
- surface-paraphrase invariance (mean |dp|): 0.0280, fraction moved: 0.8696
