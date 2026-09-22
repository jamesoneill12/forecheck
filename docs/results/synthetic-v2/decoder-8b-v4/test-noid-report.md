# forecheck evaluation report — SYNTHETIC_IN_DISTRIBUTION

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=test, n=4412, sha256=3aa19ec814b3defba069f72d0152bd73422e09930e1d42f3ad51bf8390728d60
Seed: 0. Generated at: 2026-09-22T15:33:00.535597+00:00.
Model: huggingface/ibm-granite/granite-3.3-8b-instruct
Identity stripped: true
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: test.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 4412 | 0.0882 | 0.8609 | 2.0000 | 1.0000 | 0.7558 | 0.8609 | 0.7901 | 0.8951 | n/a |
| unauthorized_scope | 4216 | 0.1191 | 0.1676 | -5.5000 | 0.1192 | 1.0000 | 0.2129 | 0.1180 | 0.4862 | 0.0333 |
| sensitive_data_exposure | 1073 | 0.2144 | 1.0000 | 8.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | n/a |
| untrusted_destination | 1367 | 0.3555 | 0.9979 | -0.5000 | 0.9959 | 1.0000 | 0.9979 | 0.9999 | 1.0000 | 0.0000 |
| privilege_escalation | 4412 | 0.0161 | 0.9045 | 9.5000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0006 |
| destructive_or_irreversible_action | 4412 | 0.1145 | 0.9788 | -1.0000 | 1.0000 | 0.9584 | 0.9788 | 0.9935 | 0.9992 | n/a |
| financial_commitment | 4412 | 0.0780 | 1.0000 | 8.0000 | 1.0000 | 0.9855 | 0.9927 | 1.0000 | 1.0000 | n/a |
| external_communication | 95 | 0.5368 | 1.0000 | 7.5000 | 1.0000 | 0.9216 | 0.9592 | 1.0000 | 1.0000 | n/a |
| policy_conflict | 752 | 0.3590 | 0.0000 | -3.5000 | 0.3590 | 1.0000 | 0.5284 | 0.3527 | 0.4678 | n/a |
| suspicious_action_sequence | 904 | 0.3208 | 0.9568 | 3.2500 | 1.0000 | 0.9069 | 0.9512 | 0.9746 | 0.9850 | 0.0003 |
| insufficient_context | 4412 | 0.0857 | 0.4118 | -0.5000 | 0.8760 | 0.2804 | 0.4248 | 0.3959 | 0.6819 | 0.0004 |

## Macro / worst slice

- macro `precision` = 0.8122
- macro `recall` = 0.7469
- macro `f1` = 0.7526
- macro `f1@selected` = 0.8097
- macro `auprc` = 0.7841
- macro `auroc` = 0.8650
- macro `brier` = 118.8627
- macro `ece` = 0.0069
- worst-slice `precision` = 0.3167 (contrastive_axis=policy_present_versus_absent)
- worst-slice `recall` = 0.3250 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1` = 0.3200 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.6591 (contrastive_axis=policy_present_versus_absent)
- worst-slice `auroc` = 0.7355 (contrastive_axis=read_versus_write)
- worst-slice `brier` = 95.0351 (contrastive_axis=reversibility)
- worst-slice `ece` = 0.0000 (contrastive_axis=known_versus_lookalike_destination)

## Consistency
- pair consistency: 0.8491 over 159 directional pairs
- counterfactual sensitivity (mean |dp|): 18.0545
- surface-paraphrase invariance (mean |dp|): 0.3799, fraction moved: 1.0000
