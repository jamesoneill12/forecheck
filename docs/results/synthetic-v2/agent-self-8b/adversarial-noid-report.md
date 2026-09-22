# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=adversarial, n=2000, sha256=7e7608c523d92ad735090c5011544940193d88815a7c6fdca72bca4a1869748e
Seed: 0. Generated at: 2026-09-22T10:51:12.374133+00:00.
Model: agent_self/ibm-granite/granite-3.3-8b-instruct
Identity stripped: true
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: adversarial.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 2000 | 0.0845 | 0.4596 | n/a | n/a | n/a | n/a | 0.4571 | 0.7916 | 0.0794 |
| unauthorized_scope | 1913 | 0.1223 | 0.1161 | n/a | n/a | n/a | n/a | 0.1219 | 0.4995 | 0.1719 |
| sensitive_data_exposure | 489 | 0.2679 | 0.1486 | n/a | n/a | n/a | n/a | 0.2803 | 0.5157 | 0.2654 |
| untrusted_destination | 632 | 0.3703 | 0.2092 | n/a | n/a | n/a | n/a | 0.4235 | 0.5541 | 0.3256 |
| privilege_escalation | 2000 | 0.0180 | 0.0456 | n/a | n/a | n/a | n/a | 0.0242 | 0.6244 | 0.1189 |
| destructive_or_irreversible_action | 2000 | 0.0990 | 0.1647 | n/a | n/a | n/a | n/a | 0.1447 | 0.6361 | 0.1359 |
| financial_commitment | 2000 | 0.0675 | 0.1713 | n/a | n/a | n/a | n/a | 0.1091 | 0.6612 | 0.1224 |
| external_communication | 40 | 0.5250 | 0.0769 | n/a | n/a | n/a | n/a | 0.4744 | 0.4398 | 0.5105 |
| policy_conflict | 343 | 0.3673 | 0.2105 | n/a | n/a | n/a | n/a | 0.3807 | 0.4918 | 0.3439 |
| suspicious_action_sequence | 402 | 0.3010 | 0.2045 | n/a | n/a | n/a | n/a | 0.2954 | 0.4861 | 0.2903 |
| insufficient_context | 2000 | 0.0870 | 0.1197 | n/a | n/a | n/a | n/a | 0.0960 | 0.5317 | 0.1539 |

## Macro / worst slice

- macro `precision` = 0.2375
- macro `recall` = 0.1760
- macro `f1` = 0.1752
- macro `f1@selected` = n/a
- macro `auprc` = 0.2552
- macro `auroc` = 0.5665
- macro `brier` = 0.2302
- macro `ece` = 0.2289
- worst-slice `precision` = 0.0000 (contrastive_axis=known_versus_lookalike_destination)
- worst-slice `recall` = 0.0000 (contrastive_axis=known_versus_lookalike_destination)
- worst-slice `f1` = 0.0000 (contrastive_axis=known_versus_lookalike_destination)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.2183 (difficulty=easy)
- worst-slice `auroc` = 0.0000 (contrastive_axis=resource_sensitivity)
- worst-slice `brier` = 0.1022 (contrastive_axis=policy_present_versus_absent)
- worst-slice `ece` = 0.1127 (contrastive_axis=resource_sensitivity)

## Consistency
- pair consistency: 0.6562 over 32 directional pairs
- counterfactual sensitivity (mean |dp|): 0.2589
- surface-paraphrase invariance (mean |dp|): 0.0522, fraction moved: 0.1429

## Self-judgment vs external checker

The agent produces one ALLOW/STOP decision per example, not per dimension; the same score is evaluated against every dimension's labels below, so this measures how well a single act/refuse decision happens to cover each dimension -- not eleven independent judgments.

| dimension | agent auprc | agent recall@selected |
|---|---|---|
| prompt_injection_influence | 0.4571 | n/a |
| unauthorized_scope | 0.1219 | n/a |
| sensitive_data_exposure | 0.2803 | n/a |
| untrusted_destination | 0.4235 | n/a |
| privilege_escalation | 0.0242 | n/a |
| destructive_or_irreversible_action | 0.1447 | n/a |
| financial_commitment | 0.1091 | n/a |
| external_communication | 0.4744 | n/a |
| policy_conflict | 0.3807 | n/a |
| suspicious_action_sequence | 0.2954 | n/a |
| insufficient_context | 0.0960 | n/a |
