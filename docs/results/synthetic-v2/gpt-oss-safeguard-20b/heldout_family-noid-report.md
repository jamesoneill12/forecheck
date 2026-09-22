# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_family, n=400, sha256=d9cc04a793e29537e02103993ac07731ff556a8429263537686fedd235f3f887
Seed: 0. Generated at: 2026-09-22T06:15:40.354937+00:00.
Model: guardian_gpt_oss_safeguard/openai/gpt-oss-safeguard-20b
Identity stripped: true
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: heldout_family.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 400 | 0.0675 | 0.3579 | n/a | n/a | n/a | n/a | 0.1824 | 0.7465 | 0.1525 |
| unauthorized_scope | 381 | 0.0971 | 0.1573 | n/a | n/a | n/a | n/a | 0.0979 | 0.5046 | 0.3937 |
| sensitive_data_exposure | 86 | 0.2093 | 0.3846 | n/a | n/a | n/a | n/a | 0.3248 | 0.6168 | 0.1860 |
| untrusted_destination | 119 | 0.3109 | 0.3934 | n/a | n/a | n/a | n/a | 0.3722 | 0.5890 | 0.3109 |
| privilege_escalation | 400 | 0.0800 | 0.2353 | n/a | n/a | n/a | n/a | 0.1187 | 0.6413 | 0.2925 |
| destructive_or_irreversible_action | 400 | 0.1075 | 0.3366 | n/a | n/a | n/a | n/a | 0.1809 | 0.6403 | 0.1675 |
| financial_commitment | 400 | 0.0825 | 0.2143 | n/a | n/a | n/a | n/a | 0.1149 | 0.5677 | 0.1100 |
| external_communication | 13 | 0.7692 | 0.7368 | n/a | n/a | n/a | n/a | 0.7752 | 0.5167 | 0.3846 |
| policy_conflict | 103 | 0.2913 | 0.1633 | n/a | n/a | n/a | n/a | 0.2805 | 0.4639 | 0.3981 |
| suspicious_action_sequence | 84 | 0.3571 | 0.4923 | n/a | n/a | n/a | n/a | 0.4105 | 0.5907 | 0.3929 |
| insufficient_context | 400 | 0.0950 | 0.1967 | n/a | n/a | n/a | n/a | 0.1101 | 0.5584 | 0.2450 |

## Macro / worst slice

- macro `precision` = 0.3423
- macro `recall` = 0.4029
- macro `f1` = 0.3335
- macro `f1@selected` = n/a
- macro `auprc` = 0.2698
- macro `auroc` = 0.5851
- macro `brier` = 0.2758
- macro `ece` = 0.2758
- worst-slice `precision` = 0.0000 (contrastive_axis=destination_tenancy)
- worst-slice `recall` = 0.0000 (contrastive_axis=destination_tenancy)
- worst-slice `f1` = 0.0000 (contrastive_axis=destination_tenancy)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.1953 (tool_family=browser)
- worst-slice `auroc` = 0.3224 (tool_family=email_messaging)
- worst-slice `brier` = 0.1111 (contrastive_axis=instruction_provenance)
- worst-slice `ece` = 0.1111 (contrastive_axis=instruction_provenance)

## Consistency
- pair consistency: 0.0000 over 1 directional pairs
- counterfactual sensitivity (mean |dp|): 0.0000
- surface-paraphrase invariance (mean |dp|): n/a, fraction moved: n/a
