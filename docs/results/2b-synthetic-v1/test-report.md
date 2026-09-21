# forecheck evaluation report — SYNTHETIC_IN_DISTRIBUTION

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=test, n=4955, sha256=111c16dd9e16e57a65191537aa6252ddbe6e437aa2546cf9c295a4cde5b2440c
Seed: 0. Generated at: 2026-09-21T17:29:38.033113+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1 | auprc | auroc | ece |
|---|---|---|---|---|---|---|
| prompt_injection_influence | 4955 | 0.0823 | 0.6306 | 0.4509 | 0.8659 | 0.0029 |
| unauthorized_scope | 4742 | 0.1141 | 1.0000 | 1.0000 | 1.0000 | 0.0007 |
| sensitive_data_exposure | 1174 | 0.2342 | 1.0000 | 1.0000 | 1.0000 | 0.0004 |
| untrusted_destination | 1509 | 0.3579 | 1.0000 | 1.0000 | 1.0000 | 0.0002 |
| privilege_escalation | 4955 | 0.0238 | 0.0000 | 0.4666 | 0.9854 | 0.0037 |
| destructive_or_irreversible_action | 4955 | 0.0953 | 0.9915 | 0.9970 | 0.9997 | 0.0011 |
| financial_commitment | 4955 | 0.0723 | 0.9986 | 1.0000 | 1.0000 | 0.0004 |
| external_communication | 122 | 0.5656 | 1.0000 | 1.0000 | 1.0000 | 0.0014 |
| policy_conflict | 1356 | 0.3385 | 0.9845 | 0.9994 | 0.9997 | 0.0040 |
| suspicious_action_sequence | 999 | 0.3043 | 0.0000 | 0.3071 | 0.5198 | 0.0188 |
| insufficient_context | 4955 | 0.0811 | 0.7602 | 0.8039 | 0.9157 | 0.0403 |

## Macro / worst slice

- macro `precision` = 0.7530
- macro `recall` = 0.7728
- macro `f1` = 0.7605
- macro `auprc` = 0.8204
- macro `auroc` = 0.9351
- macro `brier` = 0.0292
- macro `ece` = 0.0067
- worst-slice `precision` = 0.1111 (contrastive_axis=known_versus_lookalike_destination)
- worst-slice `recall` = 0.1111 (contrastive_axis=known_versus_lookalike_destination)
- worst-slice `f1` = 0.1111 (contrastive_axis=known_versus_lookalike_destination)
- worst-slice `auprc` = 0.7569 (is_benign_hard_negative)
- worst-slice `auroc` = 0.8845 (is_benign_hard_negative)
- worst-slice `brier` = 0.0001 (contrastive_axis=known_versus_lookalike_destination)
- worst-slice `ece` = 0.0053 (contrastive_axis=known_versus_lookalike_destination)

## Consistency
- pair consistency: 0.0000 over 1 directional pairs
- counterfactual sensitivity (mean |dp|): 0.5025
- surface-paraphrase invariance (mean |dp|): n/a, fraction moved: n/a
