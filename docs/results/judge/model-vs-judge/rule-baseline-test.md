# forecheck evaluation report — SYNTHETIC_IN_DISTRIBUTION

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=test, n=248, sha256=3aa19ec814b3defba069f72d0152bd73422e09930e1d42f3ad51bf8390728d60
Seed: 0. Generated at: 2026-09-22T16:25:27.035927+00:00.
Model: rule_baseline/rule-baseline-v1
Labels: llm judge gpt-5.6-sol
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: test.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 200 | 0.1000 | 0.5634 | n/a | n/a | n/a | n/a | 0.3922 | 0.9139 | 0.1795 |
| unauthorized_scope | 248 | 0.2218 | 0.4524 | n/a | n/a | n/a | n/a | 0.5129 | 0.7165 | 0.1522 |
| sensitive_data_exposure | 197 | 0.1726 | 0.1754 | n/a | n/a | n/a | n/a | 0.1566 | 0.4242 | 0.2832 |
| untrusted_destination | 67 | 0.5373 | 0.4681 | n/a | n/a | n/a | n/a | 0.6787 | 0.6528 | 0.3396 |
| privilege_escalation | 248 | 0.0444 | 0.6154 | n/a | n/a | n/a | n/a | 0.4000 | 0.8489 | 0.0601 |
| destructive_or_irreversible_action | 248 | 0.0605 | 0.5455 | n/a | n/a | n/a | n/a | 0.3085 | 0.7794 | 0.0571 |
| financial_commitment | 33 | 0.1212 | 0.2857 | n/a | n/a | n/a | n/a | 0.1627 | 0.6336 | 0.4045 |
| external_communication | 174 | 0.1264 | 0.2178 | n/a | n/a | n/a | n/a | 0.1371 | 0.5336 | 0.3368 |
| policy_conflict | 236 | 0.3941 | 0.5627 | n/a | n/a | n/a | n/a | 0.3932 | 0.4981 | 0.1097 |
| suspicious_action_sequence | 163 | 0.2699 | 0.4158 | n/a | n/a | n/a | n/a | 0.4625 | 0.6824 | 0.3233 |
| insufficient_context | 248 | 0.0685 | 0.0000 | n/a | n/a | n/a | n/a | 0.0685 | 0.4978 | 0.0226 |

## Macro / worst slice

- macro `precision` = 0.3510
- macro `recall` = 0.6192
- macro `f1` = 0.3911
- macro `f1@selected` = n/a
- macro `auprc` = 0.3339
- macro `auroc` = 0.6528
- macro `brier` = 0.2113
- macro `ece` = 0.2062
- worst-slice `precision` = 0.0000 (contrastive_axis=destination_tenancy)
- worst-slice `recall` = 0.0000 (contrastive_axis=destination_tenancy)
- worst-slice `f1` = 0.0000 (contrastive_axis=destination_tenancy)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.2099 (tool_family=crm_support)
- worst-slice `auroc` = 0.3750 (contrastive_axis=isolated_versus_sequence)
- worst-slice `brier` = 0.0541 (contrastive_axis=explicit_versus_inferred_intent)
- worst-slice `ece` = 0.1389 (contrastive_axis=policy_present_versus_absent)

## Consistency
- pair consistency: 0.0000 over 2 directional pairs
- counterfactual sensitivity (mean |dp|): 0.0000
- surface-paraphrase invariance (mean |dp|): n/a, fraction moved: n/a
