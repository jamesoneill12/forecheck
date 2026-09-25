# forecheck evaluation report — SYNTHETIC_IN_DISTRIBUTION

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=test, n=900, sha256=f0d4c5b1e9fdbf35a4a581d06da512eebb9aaf4790dbad42fa735097cb218c5c
Seed: 0. Generated at: 2026-09-25T11:47:24.353301+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: test.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 900 | 0.0767 | 0.8710 | 0.9976 | 0.9804 | 0.7246 | 0.8333 | 0.8049 | 0.9013 | 0.0052 |
| unauthorized_scope | 849 | 0.1307 | 1.0000 | 0.9047 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0002 |
| sensitive_data_exposure | 240 | 0.2042 | 1.0000 | 0.9985 | 1.0000 | 0.9184 | 0.9574 | 1.0000 | 1.0000 | 0.0008 |
| untrusted_destination | 300 | 0.3600 | 0.9907 | 0.9924 | 1.0000 | 0.9630 | 0.9811 | 0.9999 | 1.0000 | 0.0098 |
| privilege_escalation | 900 | 0.0267 | 1.0000 | 0.9047 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0002 |
| destructive_or_irreversible_action | 900 | 0.1167 | 0.9655 | 0.1620 | 0.9901 | 0.9524 | 0.9709 | 0.9919 | 0.9987 | 0.0048 |
| financial_commitment | 900 | 0.0744 | 1.0000 | 0.9994 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0002 |
| external_communication | 17 | 0.4706 | 1.0000 | 0.9985 | 1.0000 | 0.6250 | 0.7692 | 1.0000 | 1.0000 | 0.0033 |
| policy_conflict | 145 | 0.3034 | 0.8000 | 0.4105 | 0.8684 | 0.7500 | 0.8049 | 0.9035 | 0.9397 | 0.0419 |
| suspicious_action_sequence | 178 | 0.2921 | 0.8936 | 0.7396 | 1.0000 | 0.8077 | 0.8936 | 0.9619 | 0.9799 | 0.0265 |
| insufficient_context | 900 | 0.1089 | 0.8024 | 0.3774 | 0.8846 | 0.7041 | 0.7841 | 0.8272 | 0.9129 | 0.0126 |

## Macro / worst slice

- macro `precision` = 0.9848
- macro `recall` = 0.9023
- macro `f1` = 0.9385
- macro `f1@selected` = 0.9086
- macro `auprc` = 0.9536
- macro `auroc` = 0.9757
- macro `brier` = 0.0173
- macro `ece` = 0.0096
- worst-slice `precision` = 0.1000 (contrastive_axis=isolated_versus_sequence)
- worst-slice `recall` = 0.1000 (contrastive_axis=isolated_versus_sequence)
- worst-slice `f1` = 0.1000 (contrastive_axis=isolated_versus_sequence)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.6667 (contrastive_axis=explicit_versus_inferred_intent)
- worst-slice `auroc` = 0.8125 (contrastive_axis=explicit_versus_inferred_intent)
- worst-slice `brier` = 0.0003 (contrastive_axis=reversibility)
- worst-slice `ece` = 0.0089 (contrastive_axis=reversibility)

## Consistency
- pair consistency: 0.9167 over 36 directional pairs
- counterfactual sensitivity (mean |dp|): 0.8923
- surface-paraphrase invariance (mean |dp|): 0.0084, fraction moved: 0.4286

## Approval elimination

Bundle `balanced`, n=900, base incident rate=0.5667, incident rate mode=prefix. Ranking score: expected cost of ALLOW over the bundle's covered dimensions (destructive_or_irreversible_action, external_communication, financial_commitment, insufficient_context, policy_conflict, privilege_escalation, prompt_injection_influence, sensitive_data_exposure, suspicious_action_sequence, unauthorized_scope, untrusted_destination).

| budget | approvals eliminated | incident rate | review rate | deny rate |
|---|---|---|---|---|
| 0.100% | 0.0022 | 0.0000 | 0.6356 | 0.3622 |
| 0.500% | 0.0022 | 0.0000 | 0.6356 | 0.3622 |
| 1.000% | 0.0022 | 0.0000 | 0.6356 | 0.3622 |
| 2.000% | 0.0022 | 0.0000 | 0.6356 | 0.3622 |
| 5.000% | 0.2667 | 0.0500 | 0.3711 | 0.3622 |
