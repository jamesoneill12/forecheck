# forecheck evaluation report — SYNTHETIC_IN_DISTRIBUTION

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=test, n=4412, sha256=a49304db42b50d13f14c109b57a06080313a64a770702ff4a3669eb6753dc3d5
Seed: 0. Generated at: 2026-09-21T23:22:14.708124+00:00.
Model: encoder/ibm-granite/granite-embedding-english-r2
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: test.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 4412 | 0.0882 | 0.8460 | 0.9963 | 1.0000 | 0.7378 | 0.8491 | 0.8035 | 0.8735 | 0.0141 |
| unauthorized_scope | 4216 | 0.1191 | 0.9813 | 0.5876 | 0.9727 | 0.9940 | 0.9833 | 0.9992 | 0.9999 | 0.0043 |
| sensitive_data_exposure | 1073 | 0.2144 | 0.9701 | 0.7769 | 0.9912 | 0.9739 | 0.9825 | 0.9985 | 0.9996 | 0.0124 |
| untrusted_destination | 1367 | 0.3555 | 0.9774 | 0.7567 | 0.9958 | 0.9753 | 0.9854 | 0.9890 | 0.9860 | 0.0124 |
| privilege_escalation | 4412 | 0.0161 | 0.5525 | 0.7905 | 0.3855 | 0.9014 | 0.5401 | 0.4332 | 0.9885 | 0.0384 |
| destructive_or_irreversible_action | 4412 | 0.1145 | 0.9674 | 0.8861 | 0.9938 | 0.9545 | 0.9737 | 0.9935 | 0.9988 | 0.0043 |
| financial_commitment | 4412 | 0.0780 | 1.0000 | 0.9173 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0021 |
| external_communication | 95 | 0.5368 | 1.0000 | 0.5137 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0900 |
| policy_conflict | 752 | 0.3590 | 0.4513 | 0.3797 | 0.3590 | 1.0000 | 0.5284 | 0.4276 | 0.5718 | 0.1389 |
| suspicious_action_sequence | 904 | 0.3208 | 0.7456 | 0.5983 | 0.8320 | 0.7000 | 0.7603 | 0.8782 | 0.9189 | 0.0653 |
| insufficient_context | 4412 | 0.0857 | 0.5747 | 0.7384 | 0.5354 | 0.7407 | 0.6215 | 0.5851 | 0.8877 | 0.1437 |

## Macro / worst slice

- macro `precision` = 0.8025
- macro `recall` = 0.8830
- macro `f1` = 0.8242
- macro `f1@selected` = 0.8386
- macro `auprc` = 0.8280
- macro `auroc` = 0.9295
- macro `brier` = 0.0492
- macro `ece` = 0.0478
- worst-slice `precision` = 0.4000 (contrastive_axis=policy_present_versus_absent)
- worst-slice `recall` = 0.4000 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1` = 0.4000 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.7645 (difficulty=easy)
- worst-slice `auroc` = 0.8333 (contrastive_axis=read_versus_write)
- worst-slice `brier` = 0.0284 (contrastive_axis=policy_present_versus_absent)
- worst-slice `ece` = 0.0364 (tool_family=browser)

## Consistency
- pair consistency: 0.9686 over 159 directional pairs
- counterfactual sensitivity (mean |dp|): 0.8974
- surface-paraphrase invariance (mean |dp|): 0.0297, fraction moved: 0.9565
