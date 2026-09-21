# forecheck evaluation report — SYNTHETIC_IN_DISTRIBUTION

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=test, n=4967, sha256=15445b48048117c634ce5f34bfa97caa91a226493aad0f330712ea788f52fde0
Seed: 0. Generated at: 2026-09-21T23:01:51.758202+00:00.
Model: encoder/answerdotai/ModernBERT-large
Identity stripped: true
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: test.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 4967 | 0.0787 | 0.8650 | 1.1484 | 1.0000 | 0.7621 | 0.8650 | 0.8097 | 0.8816 | 0.0001 |
| unauthorized_scope | 4720 | 0.1201 | 0.2142 | 0.7500 | 0.1200 | 0.9982 | 0.2142 | 0.1140 | 0.4780 | 0.0006 |
| sensitive_data_exposure | 1186 | 0.2201 | 0.8771 | 1.1094 | 0.8893 | 0.9540 | 0.9205 | 0.9577 | 0.9901 | 0.0252 |
| untrusted_destination | 1519 | 0.3641 | 0.9900 | -0.5469 | 0.9874 | 0.9946 | 0.9910 | 0.9993 | 0.9996 | 0.0018 |
| privilege_escalation | 4967 | 0.0193 | 0.5921 | 2.5938 | 0.5048 | 0.5521 | 0.5274 | 0.5423 | 0.9897 | 0.0014 |
| destructive_or_irreversible_action | 4967 | 0.1075 | 0.9681 | 0.8633 | 0.9809 | 0.9607 | 0.9707 | 0.9908 | 0.9970 | 0.0024 |
| financial_commitment | 4967 | 0.0797 | 1.0000 | 2.9844 | 1.0000 | 0.9924 | 0.9962 | 1.0000 | 1.0000 | n/a |
| external_communication | 112 | 0.4911 | 0.9143 | -0.1836 | 0.9464 | 0.9636 | 0.9550 | 0.9907 | 0.9911 | 0.0417 |
| policy_conflict | 1364 | 0.3270 | 0.1308 | -0.2734 | 0.3479 | 0.8206 | 0.4887 | 0.3926 | 0.5861 | 0.0882 |
| suspicious_action_sequence | 1068 | 0.3099 | 0.5926 | 0.3516 | 0.6373 | 0.5891 | 0.6122 | 0.6752 | 0.7881 | 0.0497 |
| insufficient_context | 4967 | 0.0928 | 0.1692 | 4.0000 | 0.9845 | 0.2755 | 0.4305 | 0.4177 | 0.6573 | 0.0582 |

## Macro / worst slice

- macro `precision` = 0.6810
- macro `recall` = 0.8249
- macro `f1` = 0.6649
- macro `f1@selected` = 0.7247
- macro `auprc` = 0.7173
- macro `auroc` = 0.8508
- macro `brier` = 24.5872
- macro `ece` = 0.0269
- worst-slice `precision` = 0.2737 (contrastive_axis=policy_present_versus_absent)
- worst-slice `recall` = 0.4500 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1` = 0.2919 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.5870 (contrastive_axis=policy_present_versus_absent)
- worst-slice `auroc` = 0.6919 (contrastive_axis=policy_present_versus_absent)
- worst-slice `brier` = 14.7964 (contrastive_axis=financial_materiality)
- worst-slice `ece` = 0.0254 (trajectory_length=0)

## Consistency
- pair consistency: 0.8895 over 172 directional pairs
- counterfactual sensitivity (mean |dp|): 7.9733
- surface-paraphrase invariance (mean |dp|): 0.4785, fraction moved: 1.0000
