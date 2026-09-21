# forecheck evaluation report — SYNTHETIC_IN_DISTRIBUTION

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=test, n=4967, sha256=15445b48048117c634ce5f34bfa97caa91a226493aad0f330712ea788f52fde0
Seed: 0. Generated at: 2026-09-21T22:09:39.497382+00:00.
Model: encoder/answerdotai/ModernBERT-large
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: test.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 4967 | 0.0787 | 0.8654 | 0.9728 | 1.0000 | 0.7621 | 0.8650 | 0.8128 | 0.8814 | 0.0071 |
| unauthorized_scope | 4720 | 0.1201 | 0.9632 | 0.7525 | 0.9621 | 0.9841 | 0.9730 | 0.9979 | 0.9997 | 0.0092 |
| sensitive_data_exposure | 1186 | 0.2201 | 0.8808 | 0.7419 | 0.8957 | 0.9540 | 0.9239 | 0.9741 | 0.9927 | 0.0626 |
| untrusted_destination | 1519 | 0.3641 | 0.9901 | 0.5782 | 0.9909 | 0.9855 | 0.9882 | 0.9987 | 0.9989 | 0.0090 |
| privilege_escalation | 4967 | 0.0193 | 0.5968 | 0.8925 | 0.4706 | 0.6667 | 0.5517 | 0.4982 | 0.9886 | 0.0354 |
| destructive_or_irreversible_action | 4967 | 0.1075 | 0.9755 | 0.6479 | 0.9923 | 0.9644 | 0.9782 | 0.9909 | 0.9962 | 0.0039 |
| financial_commitment | 4967 | 0.0797 | 1.0000 | 0.5627 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0021 |
| external_communication | 112 | 0.4911 | 0.9630 | 0.1613 | 0.9167 | 1.0000 | 0.9565 | 0.9927 | 0.9936 | 0.0500 |
| policy_conflict | 1364 | 0.3270 | 0.4758 | 0.4553 | 0.4022 | 0.7422 | 0.5217 | 0.4230 | 0.6265 | 0.1646 |
| suspicious_action_sequence | 1068 | 0.3099 | 0.5904 | 0.5642 | 0.5710 | 0.6193 | 0.5942 | 0.6272 | 0.7697 | 0.1483 |
| insufficient_context | 4967 | 0.0928 | 0.5644 | 0.7897 | 0.5623 | 0.7050 | 0.6256 | 0.6423 | 0.9039 | 0.1360 |

## Macro / worst slice

- macro `precision` = 0.7705
- macro `recall` = 0.8798
- macro `f1` = 0.8060
- macro `f1@selected` = 0.8162
- macro `auprc` = 0.8143
- macro `auroc` = 0.9228
- macro `brier` = 0.0592
- macro `ece` = 0.0571
- worst-slice `precision` = 0.3667 (contrastive_axis=policy_present_versus_absent)
- worst-slice `recall` = 0.4500 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1` = 0.3900 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.7255 (contrastive_axis=known_versus_lookalike_destination)
- worst-slice `auroc` = 0.8687 (contrastive_axis=known_versus_lookalike_destination)
- worst-slice `brier` = 0.0453 (trajectory_length=0)
- worst-slice `ece` = 0.0470 (trajectory_length=0)

## Consistency
- pair consistency: 0.9709 over 172 directional pairs
- counterfactual sensitivity (mean |dp|): 0.8632
- surface-paraphrase invariance (mean |dp|): 0.0382, fraction moved: 0.9600
