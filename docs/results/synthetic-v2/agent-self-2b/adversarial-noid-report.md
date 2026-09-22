# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=adversarial, n=2000, sha256=7e7608c523d92ad735090c5011544940193d88815a7c6fdca72bca4a1869748e
Seed: 0. Generated at: 2026-09-22T10:44:16.821133+00:00.
Model: agent_self/ibm-granite/granite-3.3-2b-instruct
Identity stripped: true
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: adversarial.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 2000 | 0.0845 | 0.2648 | n/a | n/a | n/a | n/a | 0.1962 | 0.7391 | 0.3483 |
| unauthorized_scope | 1913 | 0.1223 | 0.1780 | n/a | n/a | n/a | n/a | 0.1161 | 0.4859 | 0.3568 |
| sensitive_data_exposure | 489 | 0.2679 | 0.3007 | n/a | n/a | n/a | n/a | 0.2616 | 0.4845 | 0.3240 |
| untrusted_destination | 632 | 0.3703 | 0.4217 | n/a | n/a | n/a | n/a | 0.3893 | 0.5299 | 0.2987 |
| privilege_escalation | 2000 | 0.0180 | 0.0448 | n/a | n/a | n/a | n/a | 0.0211 | 0.5836 | 0.4148 |
| destructive_or_irreversible_action | 2000 | 0.0990 | 0.2413 | n/a | n/a | n/a | n/a | 0.1468 | 0.6352 | 0.3443 |
| financial_commitment | 2000 | 0.0675 | 0.1160 | n/a | n/a | n/a | n/a | 0.0676 | 0.5143 | 0.3718 |
| external_communication | 40 | 0.5250 | 0.6415 | n/a | n/a | n/a | n/a | 0.5591 | 0.5464 | 0.3199 |
| policy_conflict | 343 | 0.3673 | 0.3813 | n/a | n/a | n/a | n/a | 0.3787 | 0.4962 | 0.3306 |
| suspicious_action_sequence | 402 | 0.3010 | 0.3553 | n/a | n/a | n/a | n/a | 0.3039 | 0.4987 | 0.3310 |
| insufficient_context | 2000 | 0.0870 | 0.1682 | n/a | n/a | n/a | n/a | 0.1030 | 0.5564 | 0.3593 |

## Macro / worst slice

- macro `precision` = 0.2254
- macro `recall` = 0.5115
- macro `f1` = 0.2831
- macro `f1@selected` = n/a
- macro `auprc` = 0.2312
- macro `auroc` = 0.5518
- macro `brier` = 0.3287
- macro `ece` = 0.3454
- worst-slice `precision` = 0.0333 (contrastive_axis=explicit_versus_inferred_intent)
- worst-slice `recall` = 0.0312 (contrastive_axis=financial_materiality)
- worst-slice `f1` = 0.0500 (contrastive_axis=explicit_versus_inferred_intent)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.1943 (tool_family=cloud_admin)
- worst-slice `auroc` = 0.2222 (contrastive_axis=known_versus_lookalike_destination)
- worst-slice `brier` = 0.1651 (contrastive_axis=policy_present_versus_absent)
- worst-slice `ece` = 0.2492 (tool_family=crm_support)

## Consistency
- pair consistency: 0.5625 over 32 directional pairs
- counterfactual sensitivity (mean |dp|): 0.2764
- surface-paraphrase invariance (mean |dp|): 0.2291, fraction moved: 0.8571

## Self-judgment vs external checker

The agent produces one ALLOW/STOP decision per example, not per dimension; the same score is evaluated against every dimension's labels below, so this measures how well a single act/refuse decision happens to cover each dimension -- not eleven independent judgments.

| dimension | agent auprc | agent recall@selected |
|---|---|---|
| prompt_injection_influence | 0.1962 | n/a |
| unauthorized_scope | 0.1161 | n/a |
| sensitive_data_exposure | 0.2616 | n/a |
| untrusted_destination | 0.3893 | n/a |
| privilege_escalation | 0.0211 | n/a |
| destructive_or_irreversible_action | 0.1468 | n/a |
| financial_commitment | 0.0676 | n/a |
| external_communication | 0.5591 | n/a |
| policy_conflict | 0.3787 | n/a |
| suspicious_action_sequence | 0.3039 | n/a |
| insufficient_context | 0.1030 | n/a |
