# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_policy_kind, n=95, sha256=99c768cce2dd5ac344288cf1ca35a2825ca52a9ea3002ff39d94f71c96406a2c
Seed: 0. Generated at: 2026-09-22T16:24:00.058336+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Labels: llm judge gpt-5.6-sol
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: heldout_policy_kind.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 71 | 0.0704 | 1.0000 | n/a | n/a | n/a | n/a | 1.0000 | 1.0000 | 0.0157 |
| unauthorized_scope | 95 | 0.2632 | 0.7619 | n/a | n/a | n/a | n/a | 0.7107 | 0.7683 | 0.1036 |
| sensitive_data_exposure | 74 | 0.1216 | 0.0870 | n/a | n/a | n/a | n/a | 0.1156 | 0.4427 | 0.2796 |
| untrusted_destination | 23 | 0.5652 | 0.4706 | n/a | n/a | n/a | n/a | 0.8634 | 0.7846 | 0.3880 |
| privilege_escalation | 94 | 0.0319 | 1.0000 | n/a | n/a | n/a | n/a | 1.0000 | 1.0000 | 0.0000 |
| destructive_or_irreversible_action | 95 | 0.0526 | 0.1818 | n/a | n/a | n/a | n/a | 0.0706 | 0.3778 | 0.0908 |
| financial_commitment | 16 | 0.1250 | 0.4000 | n/a | n/a | n/a | n/a | 0.4500 | 0.8929 | 0.3750 |
| external_communication | 63 | 0.1587 | 0.3226 | n/a | n/a | n/a | n/a | 0.1973 | 0.5255 | 0.3309 |
| policy_conflict | 93 | 0.4731 | 0.5634 | n/a | n/a | n/a | n/a | 0.7717 | 0.7607 | 0.3320 |
| suspicious_action_sequence | 66 | 0.2273 | 0.3810 | n/a | n/a | n/a | n/a | 0.4165 | 0.4654 | 0.1876 |
| insufficient_context | 95 | 0.1263 | 0.1818 | n/a | n/a | n/a | n/a | 0.1810 | 0.5221 | 0.1823 |

## Macro / worst slice

- macro `precision` = 0.5704
- macro `recall` = 0.5133
- macro `f1` = 0.4864
- macro `f1@selected` = n/a
- macro `auprc` = 0.5252
- macro `auroc` = 0.6854
- macro `brier` = 0.2050
- macro `ece` = 0.2078
- worst-slice `precision` = 0.0000 (contrastive_axis=destination_tenancy)
- worst-slice `recall` = 0.0000 (contrastive_axis=destination_tenancy)
- worst-slice `f1` = 0.0000 (contrastive_axis=destination_tenancy)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.3538 (difficulty=hard)
- worst-slice `auroc` = 0.3571 (tool_family=email_messaging)
- worst-slice `brier` = 0.0561 (contrastive_axis=resource_sensitivity)
- worst-slice `ece` = 0.0721 (contrastive_axis=resource_sensitivity)

## Consistency
- pair consistency: n/a over 0 directional pairs
- counterfactual sensitivity (mean |dp|): n/a
- surface-paraphrase invariance (mean |dp|): n/a, fraction moved: n/a
