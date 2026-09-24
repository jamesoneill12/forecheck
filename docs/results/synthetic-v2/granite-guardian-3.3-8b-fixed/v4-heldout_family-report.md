# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_family, n=2000, sha256=66a28203a54adb40e602b3d56419fb2f07ab8e7fa2c462dcd8978f99f3dddc04
Seed: 0. Generated at: 2026-09-24T20:42:59.182035+00:00.
Model: guardian_granite_guardian/ibm-granite/granite-guardian-3.3-8b
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: heldout_family.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 2000 | 0.0750 | 0.5378 | n/a | n/a | n/a | n/a | 0.5778 | 0.8013 | 0.0729 |
| unauthorized_scope | 1909 | 0.1058 | 0.2397 | n/a | n/a | n/a | n/a | 0.1706 | 0.7056 | 0.2425 |
| sensitive_data_exposure | 476 | 0.2143 | 0.3346 | n/a | n/a | n/a | n/a | 0.2726 | 0.6022 | 0.2344 |
| untrusted_destination | 650 | 0.3554 | 0.3666 | n/a | n/a | n/a | n/a | 0.6561 | 0.8447 | 0.2058 |
| privilege_escalation | 2000 | 0.0745 | 0.5038 | n/a | n/a | n/a | n/a | 0.3373 | 0.9228 | 0.1228 |
| destructive_or_irreversible_action | 2000 | 0.0855 | 0.3958 | n/a | n/a | n/a | n/a | 0.2780 | 0.7168 | 0.0444 |
| financial_commitment | 2000 | 0.1005 | 0.0294 | n/a | n/a | n/a | n/a | 0.7304 | 0.9781 | 0.0904 |
| external_communication | 84 | 0.5357 | 0.6250 | n/a | n/a | n/a | n/a | 0.7087 | 0.6430 | 0.1795 |
| policy_conflict | 556 | 0.3849 | 0.5000 | n/a | n/a | n/a | n/a | 0.4767 | 0.6100 | 0.1603 |
| suspicious_action_sequence | 435 | 0.3057 | 0.3691 | n/a | n/a | n/a | n/a | 0.3186 | 0.5442 | 0.1933 |
| insufficient_context | 2000 | 0.0790 | 0.1485 | n/a | n/a | n/a | n/a | 0.0853 | 0.5309 | 0.4809 |

## Macro / worst slice

- macro `precision` = 0.4684
- macro `recall` = 0.4319
- macro `f1` = 0.3682
- macro `f1@selected` = n/a
- macro `auprc` = 0.4193
- macro `auroc` = 0.7182
- macro `brier` = 0.1879
- macro `ece` = 0.1843
- worst-slice `precision` = 0.0000 (contrastive_axis=environment_stage)
- worst-slice `recall` = 0.0000 (contrastive_axis=environment_stage)
- worst-slice `f1` = 0.0000 (contrastive_axis=environment_stage)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.3736 (tool_family=browser)
- worst-slice `auroc` = 0.3563 (contrastive_axis=reversibility)
- worst-slice `brier` = 0.1032 (contrastive_axis=policy_present_versus_absent)
- worst-slice `ece` = 0.1807 (trajectory_length=1-3)

## Consistency
- pair consistency: 0.9444 over 18 directional pairs
- counterfactual sensitivity (mean |dp|): 0.1123
- surface-paraphrase invariance (mean |dp|): 0.2997, fraction moved: 1.0000
