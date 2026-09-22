# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_family, n=6653, sha256=66a28203a54adb40e602b3d56419fb2f07ab8e7fa2c462dcd8978f99f3dddc04
Seed: 0. Generated at: 2026-09-22T13:13:17.297971+00:00.
Model: encoder/answerdotai/ModernBERT-large
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_family.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 6653 | 0.0824 | 0.8678 | 0.9767 | 1.0000 | 0.7609 | 0.8642 | 0.8114 | 0.8819 | 0.0038 |
| unauthorized_scope | 6335 | 0.1084 | 0.7309 | 0.8287 | 0.7585 | 0.9141 | 0.8290 | 0.9409 | 0.9901 | 0.0778 |
| sensitive_data_exposure | 1558 | 0.2080 | 0.6817 | 0.6654 | 0.6443 | 0.7994 | 0.7135 | 0.7234 | 0.9323 | 0.1490 |
| untrusted_destination | 2172 | 0.3568 | 0.9762 | 0.2933 | 0.9551 | 0.9871 | 0.9708 | 0.9969 | 0.9979 | 0.0060 |
| privilege_escalation | 6653 | 0.0708 | 0.9733 | 0.9986 | 1.0000 | 0.9299 | 0.9637 | 0.9978 | 0.9998 | 0.0023 |
| destructive_or_irreversible_action | 6653 | 0.0875 | 0.9202 | 0.7266 | 0.9506 | 0.9588 | 0.9547 | 0.9798 | 0.9928 | 0.0149 |
| financial_commitment | 6653 | 0.0953 | 1.0000 | 0.9171 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| external_communication | 287 | 0.5226 | 0.8593 | 0.2869 | 0.7964 | 0.8867 | 0.8391 | 0.9493 | 0.9324 | 0.0834 |
| policy_conflict | 1834 | 0.3713 | 0.5363 | 0.4680 | 0.3993 | 0.8649 | 0.5464 | 0.4571 | 0.6010 | 0.1520 |
| suspicious_action_sequence | 1392 | 0.3168 | 0.5821 | 0.4024 | 0.4567 | 0.7891 | 0.5786 | 0.6595 | 0.7614 | 0.1360 |
| insufficient_context | 6653 | 0.0870 | 0.5510 | 0.6635 | 0.5034 | 0.7634 | 0.6067 | 0.6557 | 0.9081 | 0.1474 |

## Macro / worst slice

- macro `precision` = 0.7560
- macro `recall` = 0.8649
- macro `f1` = 0.7890
- macro `f1@selected` = 0.8061
- macro `auprc` = 0.8338
- macro `auroc` = 0.9089
- macro `brier` = 0.0785
- macro `ece` = 0.0702
- worst-slice `precision` = 0.3258 (contrastive_axis=financial_materiality)
- worst-slice `recall` = 0.4444 (context_length=1k-4k)
- worst-slice `f1` = 0.3658 (contrastive_axis=financial_materiality)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.7476 (tool_family=crm_support)
- worst-slice `auroc` = 0.7945 (contrastive_axis=principal_authorization)
- worst-slice `brier` = 0.0467 (contrastive_axis=environment_stage)
- worst-slice `ece` = 0.0453 (tool_family=database_warehouse)

## Consistency
- pair consistency: 1.0000 over 100 directional pairs
- counterfactual sensitivity (mean |dp|): 0.8855
- surface-paraphrase invariance (mean |dp|): 0.0353, fraction moved: 0.9091
