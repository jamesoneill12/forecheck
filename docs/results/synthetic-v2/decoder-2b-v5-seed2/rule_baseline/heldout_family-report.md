# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_family, n=6692, sha256=c35eda561f89afd8165d706b1a3ef4e851b100cf8ef9239bde1ea633372c6cd7
Seed: 0. Generated at: 2026-09-22T18:42:18.295682+00:00.
Model: rule_baseline/rule-baseline-v1
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_family.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 6692 | 0.0813 | 0.4852 | 0.9500 | 0.3578 | 0.7537 | 0.4852 | 0.2897 | 0.8170 | 0.1228 |
| unauthorized_scope | 6393 | 0.1215 | 0.2804 | 0.9500 | 1.0000 | 0.3964 | 0.5677 | 0.4838 | 0.6971 | 0.1801 |
| sensitive_data_exposure | 1521 | 0.2078 | 0.7061 | 0.5000 | 0.5458 | 1.0000 | 0.7061 | 0.7736 | 0.9466 | 0.0703 |
| untrusted_destination | 2102 | 0.3601 | 1.0000 | 0.5000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0519 |
| privilege_escalation | 6692 | 0.0693 | 0.5253 | 0.9500 | 0.4011 | 0.7608 | 0.5253 | 0.3218 | 0.8381 | 0.0990 |
| destructive_or_irreversible_action | 6692 | 0.0867 | 0.9789 | 0.5000 | 1.0000 | 0.9586 | 0.9789 | 0.9622 | 0.9793 | 0.0498 |
| financial_commitment | 6692 | 0.0865 | 1.0000 | 0.9500 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0500 |
| external_communication | 279 | 0.5054 | 0.7705 | 0.9500 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.1855 |
| policy_conflict | 1894 | 0.3025 | 0.4579 | 0.0500 | 0.3025 | 1.0000 | 0.4645 | 0.2999 | 0.4938 | 0.2040 |
| suspicious_action_sequence | 1324 | 0.2938 | 0.4542 | 0.5000 | 0.2938 | 1.0000 | 0.4542 | 0.2903 | 0.4913 | 0.4489 |
| insufficient_context | 6692 | 0.0837 | 0.2278 | 0.9500 | 1.0000 | 0.1286 | 0.2278 | 0.2015 | 0.5643 | 0.0240 |

## Macro / worst slice

- macro `precision` = 0.6095
- macro `recall` = 0.8370
- macro `f1` = 0.6260
- macro `f1@selected` = 0.6736
- macro `auprc` = 0.6021
- macro `auroc` = 0.8025
- macro `brier` = 0.1173
- macro `ece` = 0.1351
- worst-slice `precision` = 0.1797 (contrastive_axis=financial_materiality)
- worst-slice `recall` = 0.3030 (contrastive_axis=financial_materiality)
- worst-slice `f1` = 0.2152 (contrastive_axis=financial_materiality)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.4015 (contrastive_axis=resource_sensitivity)
- worst-slice `auroc` = 0.5300 (contrastive_axis=resource_sensitivity)
- worst-slice `brier` = 0.0790 (contrastive_axis=destination_tenancy)
- worst-slice `ece` = 0.1017 (contrastive_axis=destination_tenancy)

## Consistency
- pair consistency: 0.6250 over 104 directional pairs
- counterfactual sensitivity (mean |dp|): 0.5078
- surface-paraphrase invariance (mean |dp|): 0.0000, fraction moved: 0.0000
