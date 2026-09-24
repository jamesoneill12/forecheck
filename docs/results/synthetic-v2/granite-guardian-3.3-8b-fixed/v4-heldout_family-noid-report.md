# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_family, n=2000, sha256=66a28203a54adb40e602b3d56419fb2f07ab8e7fa2c462dcd8978f99f3dddc04
Seed: 0. Generated at: 2026-09-24T20:55:21.149927+00:00.
Model: guardian_granite_guardian/ibm-granite/granite-guardian-3.3-8b
Identity stripped: true
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: heldout_family.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 2000 | 0.0750 | 0.5179 | n/a | n/a | n/a | n/a | 0.5754 | 0.8036 | 0.0606 |
| unauthorized_scope | 1909 | 0.1058 | 0.1637 | n/a | n/a | n/a | n/a | 0.1044 | 0.4884 | 0.3652 |
| sensitive_data_exposure | 476 | 0.2143 | 0.3212 | n/a | n/a | n/a | n/a | 0.2710 | 0.6081 | 0.2294 |
| untrusted_destination | 650 | 0.3554 | 0.3625 | n/a | n/a | n/a | n/a | 0.6666 | 0.8586 | 0.1996 |
| privilege_escalation | 2000 | 0.0745 | 0.2691 | n/a | n/a | n/a | n/a | 0.2799 | 0.9022 | 0.1050 |
| destructive_or_irreversible_action | 2000 | 0.0855 | 0.3944 | n/a | n/a | n/a | n/a | 0.2812 | 0.7199 | 0.0402 |
| financial_commitment | 2000 | 0.1005 | 0.0195 | n/a | n/a | n/a | n/a | 0.7347 | 0.9787 | 0.0893 |
| external_communication | 84 | 0.5357 | 0.6292 | n/a | n/a | n/a | n/a | 0.7355 | 0.6707 | 0.0813 |
| policy_conflict | 556 | 0.3849 | 0.1544 | n/a | n/a | n/a | n/a | 0.4198 | 0.5548 | 0.1989 |
| suspicious_action_sequence | 435 | 0.3057 | 0.3538 | n/a | n/a | n/a | n/a | 0.3256 | 0.5519 | 0.1626 |
| insufficient_context | 2000 | 0.0790 | 0.1487 | n/a | n/a | n/a | n/a | 0.0846 | 0.5280 | 0.4485 |

## Macro / worst slice

- macro `precision` = 0.3929
- macro `recall` = 0.3481
- macro `f1` = 0.3031
- macro `f1@selected` = n/a
- macro `auprc` = 0.4072
- macro `auroc` = 0.6968
- macro `brier` = 0.1927
- macro `ece` = 0.1801
- worst-slice `precision` = 0.0000 (contrastive_axis=environment_stage)
- worst-slice `recall` = 0.0000 (contrastive_axis=environment_stage)
- worst-slice `f1` = 0.0000 (contrastive_axis=environment_stage)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.3624 (tool_family=browser)
- worst-slice `auroc` = 0.3329 (contrastive_axis=reversibility)
- worst-slice `brier` = 0.1398 (contrastive_axis=policy_present_versus_absent)
- worst-slice `ece` = 0.1750 (trajectory_length=1-3)

## Consistency
- pair consistency: 0.8889 over 18 directional pairs
- counterfactual sensitivity (mean |dp|): 0.1093
- surface-paraphrase invariance (mean |dp|): 0.3362, fraction moved: 1.0000
