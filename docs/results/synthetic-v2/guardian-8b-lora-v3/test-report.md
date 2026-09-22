# forecheck evaluation report — SYNTHETIC_IN_DISTRIBUTION

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=test, n=4412, sha256=a49304db42b50d13f14c109b57a06080313a64a770702ff4a3669eb6753dc3d5
Seed: 0. Generated at: 2026-09-22T03:23:34.622210+00:00.
Model: huggingface/ibm-granite/granite-guardian-3.3-8b
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: test.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 4412 | 0.0882 | 0.0000 | 0.1011 | 0.5375 | 0.4242 | 0.4741 | 0.4728 | 0.8217 | 0.0538 |
| unauthorized_scope | 4216 | 0.1191 | 0.0000 | 0.0788 | 0.1191 | 1.0000 | 0.2128 | 0.0864 | 0.3422 | 0.0268 |
| sensitive_data_exposure | 1073 | 0.2144 | 0.0000 | 0.2023 | 0.2500 | 0.7478 | 0.3747 | 0.3002 | 0.6147 | 0.0388 |
| untrusted_destination | 1367 | 0.3555 | 0.0000 | 0.3518 | 0.6160 | 0.7593 | 0.6802 | 0.6997 | 0.8185 | 0.0051 |
| privilege_escalation | 4412 | 0.0161 | 0.0000 | 0.0222 | 0.0794 | 0.2113 | 0.1154 | 0.0795 | 0.6705 | 0.0017 |
| destructive_or_irreversible_action | 4412 | 0.1145 | 0.0000 | 0.1151 | 0.3461 | 0.3406 | 0.3433 | 0.2931 | 0.6593 | 0.0344 |
| financial_commitment | 4412 | 0.0780 | 0.0000 | 0.0837 | 0.1617 | 0.5640 | 0.2513 | 0.1649 | 0.7186 | 0.0085 |
| external_communication | 95 | 0.5368 | 0.0000 | 0.1801 | 0.6338 | 0.8824 | 0.7377 | 0.6892 | 0.7052 | 0.3433 |
| policy_conflict | 752 | 0.3590 | 0.0000 | 0.3519 | 0.4049 | 0.7963 | 0.5368 | 0.4292 | 0.6002 | 0.0026 |
| suspicious_action_sequence | 904 | 0.3208 | 0.0000 | 0.2824 | 0.3295 | 0.9897 | 0.4944 | 0.3693 | 0.5684 | 0.0286 |
| insufficient_context | 4412 | 0.0857 | 0.0000 | 0.0621 | 0.0857 | 1.0000 | 0.1578 | 0.0820 | 0.4796 | 0.0072 |

## Macro / worst slice

- macro `precision` = 0.0000
- macro `recall` = 0.0000
- macro `f1` = 0.0000
- macro `f1@selected` = 0.3981
- macro `auprc` = 0.3333
- macro `auroc` = 0.6363
- macro `brier` = 0.1498
- macro `ece` = 0.0501
- worst-slice `precision` = 0.0000 (tool_family=browser)
- worst-slice `recall` = 0.0000 (tool_family=browser)
- worst-slice `f1` = 0.0000 (tool_family=browser)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.2841 (difficulty=easy)
- worst-slice `auroc` = 0.4803 (contrastive_axis=resource_sensitivity)
- worst-slice `brier` = 0.0948 (contrastive_axis=policy_present_versus_absent)
- worst-slice `ece` = 0.0174 (tool_family=source_control_cicd)

## Consistency
- pair consistency: 0.5597 over 159 directional pairs
- counterfactual sensitivity (mean |dp|): 0.0092
- surface-paraphrase invariance (mean |dp|): 0.0051, fraction moved: 0.0435
