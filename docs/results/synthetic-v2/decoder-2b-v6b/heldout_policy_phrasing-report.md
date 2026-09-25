# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_policy_phrasing, n=3270, sha256=9bebf277d873fd57ea1e6124b8ecc9ee81e642a8e1183f2d31f7e6994c17075c
Seed: 0. Generated at: 2026-09-25T00:47:48.819186+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_policy_phrasing.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 3270 | 0.0789 | 0.8584 | 1.0000 | 1.0000 | 0.7519 | 0.8584 | 0.7877 | 0.8866 | 0.0054 |
| unauthorized_scope | 3113 | 0.1211 | 0.9987 | 0.0017 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0018 |
| sensitive_data_exposure | 735 | 0.2163 | 0.9968 | 0.9993 | 1.0000 | 0.9811 | 0.9905 | 1.0000 | 1.0000 | 0.0011 |
| untrusted_destination | 951 | 0.3428 | 1.0000 | 0.7311 | 1.0000 | 0.9969 | 0.9985 | 1.0000 | 1.0000 | 0.0008 |
| privilege_escalation | 3270 | 0.0156 | 1.0000 | 0.9993 | 1.0000 | 0.9608 | 0.9800 | 1.0000 | 1.0000 | 0.0000 |
| destructive_or_irreversible_action | 3270 | 0.1000 | 0.9829 | 0.9990 | 1.0000 | 0.9664 | 0.9829 | 0.9936 | 0.9992 | 0.0024 |
| financial_commitment | 3270 | 0.0807 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| external_communication | 61 | 0.5410 | 1.0000 | 0.9996 | 1.0000 | 0.8788 | 0.9355 | 1.0000 | 1.0000 | 0.0005 |
| policy_conflict | 3259 | 0.3335 | 0.9363 | 0.4513 | 0.9527 | 0.9264 | 0.9394 | 0.9772 | 0.9871 | 0.0138 |
| suspicious_action_sequence | 623 | 0.3146 | 0.9434 | 0.9823 | 1.0000 | 0.8878 | 0.9405 | 0.9757 | 0.9869 | 0.0058 |
| insufficient_context | 3270 | 0.0758 | 0.8630 | 0.9831 | 0.9947 | 0.7540 | 0.8578 | 0.9316 | 0.9905 | 0.0195 |

## Macro / worst slice

- macro `precision` = 0.9954
- macro `recall` = 0.9349
- macro `f1` = 0.9618
- macro `f1@selected` = 0.9530
- macro `auprc` = 0.9696
- macro `auroc` = 0.9864
- macro `brier` = 0.0091
- macro `ece` = 0.0046
- worst-slice `precision` = 0.4000 (contrastive_axis=permission_versus_escalation)
- worst-slice `recall` = 0.4000 (contrastive_axis=permission_versus_escalation)
- worst-slice `f1` = 0.4000 (contrastive_axis=permission_versus_escalation)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.8895 (contrastive_axis=destination_tenancy)
- worst-slice `auroc` = 0.9351 (policy_absent)
- worst-slice `brier` = 0.0001 (contrastive_axis=isolated_versus_sequence)
- worst-slice `ece` = 0.0043 (contrastive_axis=isolated_versus_sequence)

## Consistency
- pair consistency: 0.9683 over 63 directional pairs
- counterfactual sensitivity (mean |dp|): 0.9132
- surface-paraphrase invariance (mean |dp|): 0.0103, fraction moved: 0.1429
