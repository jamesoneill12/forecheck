# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_policy_phrasing, n=3294, sha256=7fbe073090b3926e1a63466b386da1e8a1e85fc57458f4d6abbba730d1e8b8f6
Seed: 0. Generated at: 2026-09-22T13:14:47.722955+00:00.
Model: encoder/answerdotai/ModernBERT-large
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_policy_phrasing.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 3294 | 0.0808 | 0.8341 | 0.9767 | 1.0000 | 0.7180 | 0.8359 | 0.7639 | 0.8537 | 0.0068 |
| unauthorized_scope | 3148 | 0.1134 | 0.8892 | 0.8287 | 0.9111 | 0.9188 | 0.9149 | 0.9814 | 0.9974 | 0.0268 |
| sensitive_data_exposure | 786 | 0.2099 | 0.6932 | 0.6654 | 0.6555 | 0.8303 | 0.7326 | 0.8360 | 0.9449 | 0.1440 |
| untrusted_destination | 1021 | 0.3310 | 0.9796 | 0.2933 | 0.9466 | 0.9970 | 0.9712 | 0.9987 | 0.9993 | 0.0129 |
| privilege_escalation | 3294 | 0.0197 | 0.9624 | 0.9986 | 0.9846 | 0.9846 | 0.9846 | 0.9983 | 1.0000 | 0.0018 |
| destructive_or_irreversible_action | 3294 | 0.1078 | 0.9789 | 0.7266 | 0.9971 | 0.9746 | 0.9858 | 0.9928 | 0.9979 | 0.0027 |
| financial_commitment | 3294 | 0.0771 | 0.9941 | 0.9171 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0010 |
| external_communication | 57 | 0.4561 | 0.8519 | 0.2869 | 0.6047 | 1.0000 | 0.7536 | 0.9305 | 0.9429 | 0.1125 |
| policy_conflict | 3289 | 0.4092 | 0.5579 | 0.4680 | 0.4419 | 0.8588 | 0.5835 | 0.5058 | 0.6003 | 0.1094 |
| suspicious_action_sequence | 718 | 0.3008 | 0.5567 | 0.4024 | 0.4457 | 0.7407 | 0.5565 | 0.5550 | 0.7435 | 0.1406 |
| insufficient_context | 3294 | 0.0723 | 0.6676 | 0.6635 | 0.5950 | 0.8950 | 0.7148 | 0.7481 | 0.9773 | 0.1099 |

## Macro / worst slice

- macro `precision` = 0.7763
- macro `recall` = 0.8870
- macro `f1` = 0.8150
- macro `f1@selected` = 0.8212
- macro `auprc` = 0.8464
- macro `auroc` = 0.9143
- macro `brier` = 0.0716
- macro `ece` = 0.0608
- worst-slice `precision` = 0.1111 (contrastive_axis=permission_versus_escalation)
- worst-slice `recall` = 0.1111 (contrastive_axis=permission_versus_escalation)
- worst-slice `f1` = 0.1111 (contrastive_axis=permission_versus_escalation)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.7741 (contrastive_axis=resource_sensitivity)
- worst-slice `auroc` = 0.8333 (contrastive_axis=financial_materiality)
- worst-slice `brier` = 0.0323 (contrastive_axis=resource_sensitivity)
- worst-slice `ece` = 0.0455 (contrastive_axis=environment_stage)

## Consistency
- pair consistency: 1.0000 over 46 directional pairs
- counterfactual sensitivity (mean |dp|): 0.8361
- surface-paraphrase invariance (mean |dp|): 0.0422, fraction moved: 0.8889
