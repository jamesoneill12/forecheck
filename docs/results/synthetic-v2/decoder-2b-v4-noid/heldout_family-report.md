# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_family, n=6653, sha256=66a28203a54adb40e602b3d56419fb2f07ab8e7fa2c462dcd8978f99f3dddc04
Seed: 0. Generated at: 2026-09-22T16:33:36.572622+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: true
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_family.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 6653 | 0.0824 | 0.8678 | 1.0000 | 1.0000 | 0.7664 | 0.8678 | 0.7967 | 0.8815 | 0.0028 |
| unauthorized_scope | 6335 | 0.1084 | 0.0000 | 0.1025 | 0.1085 | 0.9956 | 0.1957 | 0.1072 | 0.4873 | 0.0207 |
| sensitive_data_exposure | 1558 | 0.2080 | 1.0000 | 0.9859 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0046 |
| untrusted_destination | 2172 | 0.3568 | 0.9942 | 0.0525 | 0.9923 | 0.9923 | 0.9923 | 0.9978 | 0.9984 | 0.0015 |
| privilege_escalation | 6653 | 0.0708 | 0.9989 | 0.9988 | 1.0000 | 0.9979 | 0.9989 | 1.0000 | 1.0000 | 0.0020 |
| destructive_or_irreversible_action | 6653 | 0.0875 | 0.9807 | 0.4136 | 1.0000 | 0.9622 | 0.9807 | 0.9910 | 0.9990 | 0.0023 |
| financial_commitment | 6653 | 0.0953 | 1.0000 | 0.9996 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0001 |
| external_communication | 287 | 0.5226 | 1.0000 | 0.9997 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0199 |
| policy_conflict | 1834 | 0.3713 | 0.5416 | 0.5000 | 0.3713 | 1.0000 | 0.5416 | 0.4294 | 0.5849 | 0.2627 |
| suspicious_action_sequence | 1392 | 0.3168 | 0.9348 | 1.0000 | 1.0000 | 0.8776 | 0.9348 | 0.9472 | 0.9695 | 0.0052 |
| insufficient_context | 6653 | 0.0870 | 0.4415 | 0.1731 | 0.9483 | 0.2850 | 0.4382 | 0.3566 | 0.6436 | 0.0037 |

## Macro / worst slice

- macro `precision` = 0.8516
- macro `recall` = 0.8072
- macro `f1` = 0.7963
- macro `f1@selected` = 0.8136
- macro `auprc` = 0.7842
- macro `auroc` = 0.8695
- macro `brier` = 0.0473
- macro `ece` = 0.0296
- worst-slice `precision` = 0.2727 (contrastive_axis=financial_materiality)
- worst-slice `recall` = 0.2727 (contrastive_axis=financial_materiality)
- worst-slice `f1` = 0.2727 (contrastive_axis=financial_materiality)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.4811 (contrastive_axis=resource_sensitivity)
- worst-slice `auroc` = 0.5292 (contrastive_axis=resource_sensitivity)
- worst-slice `brier` = 0.0110 (contrastive_axis=policy_present_versus_absent)
- worst-slice `ece` = 0.0195 (policy_absent)

## Consistency
- pair consistency: 0.8600 over 100 directional pairs
- counterfactual sensitivity (mean |dp|): 0.8235
- surface-paraphrase invariance (mean |dp|): 0.0088, fraction moved: 0.6364

## Approval elimination

Bundle `balanced`, n=6653, base incident rate=0.5876, incident rate mode=prefix. Ranking score: expected cost of ALLOW over the bundle's covered dimensions (destructive_or_irreversible_action, external_communication, financial_commitment, insufficient_context, policy_conflict, privilege_escalation, prompt_injection_influence, sensitive_data_exposure, suspicious_action_sequence, unauthorized_scope, untrusted_destination).

| budget | approvals eliminated | incident rate | review rate | deny rate |
|---|---|---|---|---|
| 0.100% | 0.0005 | 0.0000 | 0.6027 | 0.3968 |
| 0.500% | 0.0005 | 0.0000 | 0.6027 | 0.3968 |
| 1.000% | 0.0005 | 0.0000 | 0.6027 | 0.3968 |
| 2.000% | 0.0005 | 0.0000 | 0.6027 | 0.3968 |
| 5.000% | 0.0005 | 0.0000 | 0.6027 | 0.3968 |
