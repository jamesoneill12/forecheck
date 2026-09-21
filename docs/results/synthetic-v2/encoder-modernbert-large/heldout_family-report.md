# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_family, n=6640, sha256=d9cc04a793e29537e02103993ac07731ff556a8429263537686fedd235f3f887
Seed: 0. Generated at: 2026-09-21T22:10:50.137212+00:00.
Model: encoder/answerdotai/ModernBERT-large
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_family.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 6640 | 0.0840 | 0.8727 | 0.9728 | 1.0000 | 0.7724 | 0.8716 | 0.8228 | 0.8928 | 0.0020 |
| unauthorized_scope | 6315 | 0.1123 | 0.8176 | 0.7525 | 0.7707 | 0.9859 | 0.8651 | 0.9868 | 0.9980 | 0.0502 |
| sensitive_data_exposure | 1540 | 0.2143 | 0.9006 | 0.7419 | 0.9542 | 0.8212 | 0.8827 | 0.9509 | 0.9746 | 0.0258 |
| untrusted_destination | 2109 | 0.3580 | 0.9908 | 0.5782 | 0.9921 | 0.9921 | 0.9921 | 0.9995 | 0.9997 | 0.0103 |
| privilege_escalation | 6640 | 0.0637 | 0.4006 | 0.8925 | 1.0000 | 0.0047 | 0.0094 | 0.4623 | 0.9469 | 0.0174 |
| destructive_or_irreversible_action | 6640 | 0.0907 | 0.8325 | 0.6479 | 0.7986 | 0.9684 | 0.8754 | 0.9814 | 0.9940 | 0.0376 |
| financial_commitment | 6640 | 0.0875 | 1.0000 | 0.5627 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0016 |
| external_communication | 284 | 0.5775 | 0.9241 | 0.1613 | 0.9277 | 0.9390 | 0.9333 | 0.9899 | 0.9861 | 0.0546 |
| policy_conflict | 1891 | 0.3178 | 0.4576 | 0.4553 | 0.3970 | 0.6506 | 0.4931 | 0.3989 | 0.6256 | 0.1501 |
| suspicious_action_sequence | 1289 | 0.3313 | 0.6205 | 0.5642 | 0.6484 | 0.6089 | 0.6280 | 0.6864 | 0.7795 | 0.1186 |
| insufficient_context | 6640 | 0.0861 | 0.5752 | 0.7897 | 0.5403 | 0.7150 | 0.6155 | 0.6642 | 0.9187 | 0.1605 |

## Macro / worst slice

- macro `precision` = 0.7470
- macro `recall` = 0.8068
- macro `f1` = 0.7629
- macro `f1@selected` = 0.7424
- macro `auprc` = 0.8130
- macro `auroc` = 0.9196
- macro `brier` = 0.0672
- macro `ece` = 0.0572
- worst-slice `precision` = 0.3545 (contrastive_axis=financial_materiality)
- worst-slice `recall` = 0.4242 (contrastive_axis=financial_materiality)
- worst-slice `f1` = 0.3788 (contrastive_axis=financial_materiality)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.7317 (tool_family=payments_procurement)
- worst-slice `auroc` = 0.7500 (contrastive_axis=resource_sensitivity)
- worst-slice `brier` = 0.0552 (trajectory_length=0)
- worst-slice `ece` = 0.0462 (tool_family=mcp)

## Consistency
- pair consistency: 0.9623 over 106 directional pairs
- counterfactual sensitivity (mean |dp|): 0.8784
- surface-paraphrase invariance (mean |dp|): 0.0336, fraction moved: 1.0000
