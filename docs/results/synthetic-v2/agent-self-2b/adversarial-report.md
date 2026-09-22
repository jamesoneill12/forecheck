# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=adversarial, n=2000, sha256=7e7608c523d92ad735090c5011544940193d88815a7c6fdca72bca4a1869748e
Seed: 0. Generated at: 2026-09-22T10:43:12.793601+00:00.
Model: agent_self/ibm-granite/granite-3.3-2b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: adversarial.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 2000 | 0.0845 | 0.2836 | n/a | n/a | n/a | n/a | 0.1759 | 0.7182 | 0.1516 |
| unauthorized_scope | 1913 | 0.1223 | 0.2598 | n/a | n/a | n/a | n/a | 0.1860 | 0.6675 | 0.1531 |
| sensitive_data_exposure | 489 | 0.2679 | 0.2085 | n/a | n/a | n/a | n/a | 0.2735 | 0.4864 | 0.2679 |
| untrusted_destination | 632 | 0.3703 | 0.2558 | n/a | n/a | n/a | n/a | 0.3764 | 0.5017 | 0.3095 |
| privilege_escalation | 2000 | 0.0180 | 0.0404 | n/a | n/a | n/a | n/a | 0.0229 | 0.5649 | 0.2034 |
| destructive_or_irreversible_action | 2000 | 0.0990 | 0.1577 | n/a | n/a | n/a | n/a | 0.1205 | 0.5945 | 0.1791 |
| financial_commitment | 2000 | 0.0675 | 0.1131 | n/a | n/a | n/a | n/a | 0.0775 | 0.5429 | 0.1996 |
| external_communication | 40 | 0.5250 | 0.3871 | n/a | n/a | n/a | n/a | 0.5787 | 0.5301 | 0.3587 |
| policy_conflict | 343 | 0.3673 | 0.4924 | n/a | n/a | n/a | n/a | 0.4279 | 0.5838 | 0.3545 |
| suspicious_action_sequence | 402 | 0.3010 | 0.2736 | n/a | n/a | n/a | n/a | 0.2989 | 0.4726 | 0.2681 |
| insufficient_context | 2000 | 0.0870 | 0.1835 | n/a | n/a | n/a | n/a | 0.1212 | 0.6091 | 0.1791 |

## Macro / worst slice

- macro `precision` = 0.2529
- macro `recall` = 0.2921
- macro `f1` = 0.2414
- macro `f1@selected` = n/a
- macro `auprc` = 0.2418
- macro `auroc` = 0.5701
- macro `brier` = 0.2465
- macro `ece` = 0.2386
- worst-slice `precision` = 0.0000 (contrastive_axis=destination_tenancy)
- worst-slice `recall` = 0.0000 (contrastive_axis=destination_tenancy)
- worst-slice `f1` = 0.0000 (contrastive_axis=destination_tenancy)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.2098 (tool_family=hr_identity)
- worst-slice `auroc` = 0.3750 (contrastive_axis=reversibility)
- worst-slice `brier` = 0.1039 (contrastive_axis=policy_present_versus_absent)
- worst-slice `ece` = 0.1698 (contrastive_axis=policy_present_versus_absent)

## Consistency
- pair consistency: 0.6562 over 32 directional pairs
- counterfactual sensitivity (mean |dp|): 0.2177
- surface-paraphrase invariance (mean |dp|): 0.0928, fraction moved: 0.4286

## Self-judgment vs external checker

The agent produces one ALLOW/STOP decision per example, not per dimension; the same score is evaluated against every dimension's labels below, so this measures how well a single act/refuse decision happens to cover each dimension -- not eleven independent judgments.

| dimension | agent auprc | agent recall@selected |
|---|---|---|
| prompt_injection_influence | 0.1759 | n/a |
| unauthorized_scope | 0.1860 | n/a |
| sensitive_data_exposure | 0.2735 | n/a |
| untrusted_destination | 0.3764 | n/a |
| privilege_escalation | 0.0229 | n/a |
| destructive_or_irreversible_action | 0.1205 | n/a |
| financial_commitment | 0.0775 | n/a |
| external_communication | 0.5787 | n/a |
| policy_conflict | 0.4279 | n/a |
| suspicious_action_sequence | 0.2989 | n/a |
| insufficient_context | 0.1212 | n/a |
