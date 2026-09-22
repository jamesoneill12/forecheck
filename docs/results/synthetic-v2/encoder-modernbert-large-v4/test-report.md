# forecheck evaluation report — SYNTHETIC_IN_DISTRIBUTION

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=test, n=4412, sha256=3aa19ec814b3defba069f72d0152bd73422e09930e1d42f3ad51bf8390728d60
Seed: 0. Generated at: 2026-09-22T13:12:00.078322+00:00.
Model: encoder/answerdotai/ModernBERT-large
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: test.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 4412 | 0.0882 | 0.8584 | 0.9767 | 1.0000 | 0.7558 | 0.8609 | 0.8066 | 0.8828 | 0.0048 |
| unauthorized_scope | 4216 | 0.1191 | 0.9042 | 0.8287 | 0.9433 | 0.9283 | 0.9357 | 0.9875 | 0.9980 | 0.0239 |
| sensitive_data_exposure | 1073 | 0.2144 | 0.7026 | 0.6654 | 0.6679 | 0.7783 | 0.7189 | 0.8129 | 0.9376 | 0.1273 |
| untrusted_destination | 1367 | 0.3555 | 0.9877 | 0.2933 | 0.9757 | 0.9918 | 0.9837 | 0.9992 | 0.9996 | 0.0075 |
| privilege_escalation | 4412 | 0.0161 | 0.9793 | 0.9986 | 1.0000 | 0.9859 | 0.9929 | 0.9996 | 1.0000 | 0.0008 |
| destructive_or_irreversible_action | 4412 | 0.1145 | 0.9689 | 0.7266 | 0.9918 | 0.9525 | 0.9717 | 0.9861 | 0.9957 | 0.0054 |
| financial_commitment | 4412 | 0.0780 | 0.9956 | 0.9171 | 1.0000 | 0.9971 | 0.9985 | 1.0000 | 1.0000 | 0.0006 |
| external_communication | 95 | 0.5368 | 0.8172 | 0.2869 | 0.7797 | 0.9020 | 0.8364 | 0.9285 | 0.9060 | 0.0952 |
| policy_conflict | 752 | 0.3590 | 0.4971 | 0.4680 | 0.3789 | 0.8000 | 0.5143 | 0.4371 | 0.5829 | 0.1516 |
| suspicious_action_sequence | 904 | 0.3208 | 0.5613 | 0.4024 | 0.4685 | 0.7448 | 0.5752 | 0.5940 | 0.7337 | 0.1169 |
| insufficient_context | 4412 | 0.0857 | 0.5855 | 0.6635 | 0.5378 | 0.7725 | 0.6341 | 0.6698 | 0.9041 | 0.1334 |

## Macro / worst slice

- macro `precision` = 0.7851
- macro `recall` = 0.8531
- macro `f1` = 0.8053
- macro `f1@selected` = 0.8202
- macro `auprc` = 0.8383
- macro `auroc` = 0.9037
- macro `brier` = 0.0746
- macro `ece` = 0.0607
- worst-slice `precision` = 0.3800 (contrastive_axis=policy_present_versus_absent)
- worst-slice `recall` = 0.4000 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1` = 0.3889 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.7427 (contrastive_axis=principal_authorization)
- worst-slice `auroc` = 0.7740 (contrastive_axis=reversibility)
- worst-slice `brier` = 0.0503 (contrastive_axis=policy_present_versus_absent)
- worst-slice `ece` = 0.0540 (tool_family=browser)

## Consistency
- pair consistency: 0.9748 over 159 directional pairs
- counterfactual sensitivity (mean |dp|): 0.8800
- surface-paraphrase invariance (mean |dp|): 0.0363, fraction moved: 0.9130
