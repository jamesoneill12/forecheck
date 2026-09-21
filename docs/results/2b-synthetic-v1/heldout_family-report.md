# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_family, n=2290, sha256=d5e21670e7e4762b80afa70a91ec177f484d6e56028dd5c00f3523d592e5c391
Seed: 0. Generated at: 2026-09-21T17:56:45.638081+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1 | auprc | auroc | ece |
|---|---|---|---|---|---|---|
| prompt_injection_influence | 2290 | 0.0782 | 0.6118 | 0.4011 | 0.8347 | 0.0058 |
| unauthorized_scope | 2185 | 0.1080 | 1.0000 | 1.0000 | 1.0000 | 0.0006 |
| sensitive_data_exposure | 471 | 0.2208 | 1.0000 | 1.0000 | 1.0000 | 0.0003 |
| untrusted_destination | 608 | 0.3569 | 1.0000 | 1.0000 | 1.0000 | 0.0002 |
| privilege_escalation | 2290 | 0.0000 | 0.0000 | n/a | n/a | 0.0000 |
| destructive_or_irreversible_action | 2290 | 0.0463 | 0.9856 | 0.9939 | 0.9997 | 0.0013 |
| financial_commitment | 2290 | 0.1105 | 0.9980 | 1.0000 | 1.0000 | 0.0007 |
| external_communication | 0 | n/a | n/a | n/a | n/a | n/a |
| policy_conflict | 617 | 0.3015 | 0.9836 | 0.9982 | 0.9993 | 0.0051 |
| suspicious_action_sequence | 451 | 0.2572 | 0.0000 | 0.2554 | 0.4935 | 0.0664 |
| insufficient_context | 2290 | 0.0886 | 0.7602 | 0.7898 | 0.9081 | 0.0321 |

## Macro / worst slice

- macro `precision` = 0.7313
- macro `recall` = 0.7400
- macro `f1` = 0.7339
- macro `auprc` = 0.8265
- macro `auroc` = 0.9150
- macro `brier` = 0.0293
- macro `ece` = 0.0112
- worst-slice `precision` = 0.6303 (policy_absent)
- worst-slice `recall` = 0.6352 (policy_absent)
- worst-slice `f1` = 0.6316 (policy_absent)
- worst-slice `auprc` = 0.7588 (policy_absent)
- worst-slice `auroc` = 0.8725 (policy_absent)
- worst-slice `brier` = 0.0108 (trajectory_length=0)
- worst-slice `ece` = 0.0053 (trajectory_length=0)

## Consistency
- pair consistency: n/a over 0 directional pairs
- counterfactual sensitivity (mean |dp|): n/a
- surface-paraphrase invariance (mean |dp|): n/a, fraction moved: n/a
