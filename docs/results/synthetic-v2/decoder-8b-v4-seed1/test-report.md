# forecheck evaluation report — SYNTHETIC_IN_DISTRIBUTION

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=test, n=4412, sha256=3aa19ec814b3defba069f72d0152bd73422e09930e1d42f3ad51bf8390728d60
Seed: 0. Generated at: 2026-09-23T02:18:58.854516+00:00.
Model: huggingface/ibm-granite/granite-3.3-8b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: test.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 4412 | 0.0882 | 0.8609 | 0.9997 | 1.0000 | 0.7558 | 0.8609 | 0.7898 | 0.8922 | 0.0003 |
| unauthorized_scope | 4216 | 0.1191 | 0.9734 | 0.0425 | 1.0000 | 0.9980 | 0.9990 | 1.0000 | 1.0000 | 0.0066 |
| sensitive_data_exposure | 1073 | 0.2144 | 0.9978 | 0.9495 | 1.0000 | 0.9957 | 0.9978 | 1.0000 | 1.0000 | 0.0008 |
| untrusted_destination | 1367 | 0.3555 | 0.9897 | 0.1256 | 0.9918 | 0.9979 | 0.9949 | 0.9999 | 0.9999 | 0.0072 |
| privilege_escalation | 4412 | 0.0161 | 1.0000 | 0.9996 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| destructive_or_irreversible_action | 4412 | 0.1145 | 0.9808 | 0.4334 | 1.0000 | 0.9624 | 0.9808 | 0.9950 | 0.9994 | 0.0023 |
| financial_commitment | 4412 | 0.0780 | 0.9927 | 0.0242 | 1.0000 | 0.9971 | 0.9985 | 1.0000 | 1.0000 | 0.0010 |
| external_communication | 95 | 0.5368 | 0.9800 | 0.9444 | 1.0000 | 0.9608 | 0.9800 | 1.0000 | 1.0000 | 0.0179 |
| policy_conflict | 752 | 0.3590 | 0.9623 | 0.9555 | 0.9882 | 0.9296 | 0.9580 | 0.9922 | 0.9955 | 0.0171 |
| suspicious_action_sequence | 904 | 0.3208 | 0.9550 | 0.9720 | 1.0000 | 0.9103 | 0.9531 | 0.9728 | 0.9848 | 0.0068 |
| insufficient_context | 4412 | 0.0857 | 0.5950 | 0.2486 | 0.6648 | 0.6138 | 0.6382 | 0.6822 | 0.8948 | 0.0223 |

## Macro / worst slice

- macro `precision` = 0.9809
- macro `recall` = 0.9019
- macro `f1` = 0.9352
- macro `f1@selected` = 0.9419
- macro `auprc` = 0.9484
- macro `auroc` = 0.9788
- macro `brier` = 0.0127
- macro `ece` = 0.0075
- worst-slice `precision` = 0.4000 (contrastive_axis=policy_present_versus_absent)
- worst-slice `recall` = 0.4000 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1` = 0.4000 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.8111 (contrastive_axis=policy_present_versus_absent)
- worst-slice `auroc` = 0.8833 (contrastive_axis=policy_present_versus_absent)
- worst-slice `brier` = 0.0009 (contrastive_axis=surface_paraphrase)
- worst-slice `ece` = 0.0066 (trajectory_length=4-10)

## Consistency
- pair consistency: 0.9686 over 159 directional pairs
- counterfactual sensitivity (mean |dp|): 0.9096
- surface-paraphrase invariance (mean |dp|): 0.0014, fraction moved: 0.0435
