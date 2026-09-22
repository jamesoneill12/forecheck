# forecheck evaluation report — SYNTHETIC_IN_DISTRIBUTION

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=test, n=4412, sha256=3aa19ec814b3defba069f72d0152bd73422e09930e1d42f3ad51bf8390728d60
Seed: 0. Generated at: 2026-09-22T16:45:32.925550+00:00.
Model: rule_baseline/rule-baseline-v1
Identity stripped: true
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: test.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 4412 | 0.0882 | 0.4925 | 0.9500 | 0.3652 | 0.7558 | 0.4925 | 0.2976 | 0.8144 | 0.1260 |
| unauthorized_scope | 4216 | 0.1191 | 0.2739 | 0.9500 | 1.0000 | 0.3645 | 0.5343 | 0.4554 | 0.6896 | 0.1810 |
| sensitive_data_exposure | 1073 | 0.2144 | 0.6980 | 0.5000 | 0.5361 | 1.0000 | 0.6980 | 0.7352 | 0.9354 | 0.0646 |
| untrusted_destination | 1367 | 0.3555 | 1.0000 | 0.5000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0533 |
| privilege_escalation | 4412 | 0.0161 | 0.5936 | 0.9500 | 0.4392 | 0.9155 | 0.5936 | 0.4034 | 0.9482 | 0.0641 |
| destructive_or_irreversible_action | 4412 | 0.1145 | 0.9221 | 0.5000 | 1.0000 | 0.8554 | 0.9221 | 0.8720 | 0.9277 | 0.0378 |
| financial_commitment | 4412 | 0.0780 | 1.0000 | 0.9500 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0500 |
| external_communication | 95 | 0.5368 | 0.8031 | 0.9500 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.1684 |
| policy_conflict | 752 | 0.3590 | 0.5294 | 0.0500 | 0.3590 | 1.0000 | 0.5284 | 0.3619 | 0.5061 | 0.1392 |
| suspicious_action_sequence | 904 | 0.3208 | 0.4858 | 0.5000 | 0.3208 | 1.0000 | 0.4858 | 0.3283 | 0.5165 | 0.4112 |
| insufficient_context | 4412 | 0.0857 | 0.2540 | 0.9500 | 1.0000 | 0.1455 | 0.2540 | 0.2187 | 0.5728 | 0.0245 |

## Macro / worst slice

- macro `precision` = 0.6244
- macro `recall` = 0.8452
- macro `f1` = 0.6411
- macro `f1@selected` = 0.6826
- macro `auprc` = 0.6066
- macro `auroc` = 0.8101
- macro `brier` = 0.1098
- macro `ece` = 0.1200
- worst-slice `precision` = 0.2018 (contrastive_axis=policy_present_versus_absent)
- worst-slice `recall` = 0.3750 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1` = 0.2417 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.5390 (tool_family=payments_procurement)
- worst-slice `auroc` = 0.6494 (contrastive_axis=destination_tenancy)
- worst-slice `brier` = 0.0770 (trajectory_length=0)
- worst-slice `ece` = 0.0920 (trajectory_length=0)

## Consistency
- pair consistency: 0.6101 over 159 directional pairs
- counterfactual sensitivity (mean |dp|): 0.5045
- surface-paraphrase invariance (mean |dp|): 0.0000, fraction moved: 0.0000
