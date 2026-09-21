# forecheck evaluation report — SYNTHETIC_IN_DISTRIBUTION

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=test, n=4967, sha256=15445b48048117c634ce5f34bfa97caa91a226493aad0f330712ea788f52fde0
Seed: 0. Generated at: 2026-09-21T22:42:49.680866+00:00.
Model: rule_baseline/rule-baseline-v1
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: test.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 4967 | 0.0787 | 0.4946 | 0.9500 | 0.3655 | 0.7647 | 0.4946 | 0.2980 | 0.8256 | 0.1195 |
| unauthorized_scope | 4720 | 0.1201 | 0.2889 | 0.9500 | 1.0000 | 0.4180 | 0.5896 | 0.5037 | 0.7153 | 0.1757 |
| sensitive_data_exposure | 1186 | 0.2201 | 0.7383 | 0.5000 | 0.5852 | 1.0000 | 0.7383 | 0.7664 | 0.9460 | 0.0511 |
| untrusted_destination | 1519 | 0.3641 | 1.0000 | 0.5000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0524 |
| privilege_escalation | 4967 | 0.0193 | 0.5827 | 0.9500 | 0.4451 | 0.8438 | 0.5827 | 0.3785 | 0.9115 | 0.0637 |
| destructive_or_irreversible_action | 4967 | 0.1075 | 0.9212 | 0.5000 | 1.0000 | 0.8539 | 0.9212 | 0.8696 | 0.9270 | 0.0382 |
| financial_commitment | 4967 | 0.0797 | 1.0000 | 0.9500 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0500 |
| external_communication | 112 | 0.4911 | 0.7534 | 0.9500 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.1946 |
| policy_conflict | 1364 | 0.3270 | 0.4958 | 0.0500 | 0.3270 | 1.0000 | 0.4928 | 0.3308 | 0.5086 | 0.1679 |
| suspicious_action_sequence | 1068 | 0.3099 | 0.4732 | 0.5000 | 0.3099 | 1.0000 | 0.4732 | 0.2946 | 0.4580 | 0.3670 |
| insufficient_context | 4967 | 0.0928 | 0.3020 | 0.9500 | 1.0000 | 0.1779 | 0.3020 | 0.2542 | 0.5889 | 0.0280 |

## Macro / worst slice

- macro `precision` = 0.6205
- macro `recall` = 0.8447
- macro `f1` = 0.6409
- macro `f1@selected` = 0.6904
- macro `auprc` = 0.6087
- macro `auroc` = 0.8074
- macro `brier` = 0.1074
- macro `ece` = 0.1189
- worst-slice `precision` = 0.1950 (contrastive_axis=policy_present_versus_absent)
- worst-slice `recall` = 0.3500 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1` = 0.2333 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.5209 (contrastive_axis=read_versus_write)
- worst-slice `auroc` = 0.6786 (contrastive_axis=policy_present_versus_absent)
- worst-slice `brier` = 0.0774 (trajectory_length=0)
- worst-slice `ece` = 0.0943 (trajectory_length=0)

## Consistency
- pair consistency: 0.6279 over 172 directional pairs
- counterfactual sensitivity (mean |dp|): 0.4916
- surface-paraphrase invariance (mean |dp|): 0.0000, fraction moved: 0.0000
