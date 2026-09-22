# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_policy_kind, n=2321, sha256=6c927ac4ec27ba92e7d3f68a24e047d7c15da921f0a26b5f8a909f2ddef49776
Seed: 0. Generated at: 2026-09-22T13:46:14.706838+00:00.
Model: rule_baseline/rule-baseline-v1
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_policy_kind.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 2321 | 0.0840 | 0.4824 | 0.9500 | 0.3582 | 0.7385 | 0.4824 | 0.2865 | 0.8086 | 0.1219 |
| unauthorized_scope | 2228 | 0.1095 | 0.2545 | 0.9500 | 1.0000 | 0.4221 | 0.5937 | 0.4960 | 0.6984 | 0.1862 |
| sensitive_data_exposure | 561 | 0.2103 | 0.6941 | 0.5000 | 0.5315 | 1.0000 | 0.6941 | 0.7340 | 0.9368 | 0.0683 |
| untrusted_destination | 704 | 0.3494 | 1.0000 | 0.5000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0519 |
| privilege_escalation | 2321 | 0.0164 | 0.5079 | 0.9500 | 0.3636 | 0.8421 | 0.5079 | 0.3088 | 0.9088 | 0.0678 |
| destructive_or_irreversible_action | 2321 | 0.1004 | 0.9035 | 0.5000 | 1.0000 | 0.8240 | 0.9035 | 0.8417 | 0.9120 | 0.0370 |
| financial_commitment | 2321 | 0.0681 | 1.0000 | 0.9500 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0500 |
| external_communication | 54 | 0.6296 | 0.8293 | 0.9500 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.1667 |
| policy_conflict | 2316 | 0.3303 | 0.4858 | 0.0500 | 0.3303 | 1.0000 | 0.4966 | 0.3253 | 0.4885 | 0.1825 |
| suspicious_action_sequence | 463 | 0.3305 | 0.4968 | 0.5000 | 0.3305 | 1.0000 | 0.4968 | 0.3412 | 0.5228 | 0.3970 |
| insufficient_context | 2321 | 0.0689 | 0.3420 | 0.9500 | 1.0000 | 0.2062 | 0.3420 | 0.2610 | 0.6031 | 0.0061 |

## Macro / worst slice

- macro `precision` = 0.6160
- macro `recall` = 0.8370
- macro `f1` = 0.6360
- macro `f1@selected` = 0.6834
- macro `auprc` = 0.5995
- macro `auroc` = 0.8072
- macro `brier` = 0.1077
- macro `ece` = 0.1214
- worst-slice `precision` = 0.1500 (contrastive_axis=policy_present_versus_absent)
- worst-slice `recall` = 0.1667 (contrastive_axis=environment_stage)
- worst-slice `f1` = 0.1667 (contrastive_axis=environment_stage)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.2639 (contrastive_axis=explicit_versus_inferred_intent)
- worst-slice `auroc` = 0.5278 (contrastive_axis=explicit_versus_inferred_intent)
- worst-slice `brier` = 0.0497 (contrastive_axis=policy_present_versus_absent)
- worst-slice `ece` = 0.0744 (contrastive_axis=surface_paraphrase)

## Consistency
- pair consistency: 0.5938 over 32 directional pairs
- counterfactual sensitivity (mean |dp|): 0.4629
- surface-paraphrase invariance (mean |dp|): 0.0000, fraction moved: 0.0000
