# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_policy_kind, n=2321, sha256=258aaaafb056fc6678c439f95e60ed2b0cb212a789c0d86feb7c204fe5309de2
Seed: 0. Generated at: 2026-09-23T05:46:59.369896+00:00.
Model: huggingface/ibm-granite/granite-3.3-8b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_policy_kind.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 2321 | 0.0840 | 0.8462 | 0.1079 | 1.0000 | 0.7333 | 0.8462 | 0.7723 | 0.8820 | 0.0065 |
| unauthorized_scope | 2228 | 0.1095 | 0.9938 | 0.0250 | 1.0000 | 0.9959 | 0.9979 | 1.0000 | 1.0000 | 0.0035 |
| sensitive_data_exposure | 561 | 0.2103 | 1.0000 | 0.1192 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0002 |
| untrusted_destination | 704 | 0.3494 | 0.9939 | 0.0517 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0044 |
| privilege_escalation | 2321 | 0.0164 | 0.9867 | 0.9948 | 1.0000 | 0.9737 | 0.9867 | 0.9793 | 0.9984 | 0.0004 |
| destructive_or_irreversible_action | 2321 | 0.1004 | 0.9847 | 0.1742 | 1.0000 | 0.9700 | 0.9847 | 0.9936 | 0.9992 | 0.0018 |
| financial_commitment | 2321 | 0.0681 | 0.9968 | 0.3775 | 1.0000 | 0.9937 | 0.9968 | 1.0000 | 1.0000 | 0.0004 |
| external_communication | 54 | 0.6296 | 1.0000 | 0.9988 | 1.0000 | 0.9706 | 0.9851 | 1.0000 | 1.0000 | 0.0003 |
| policy_conflict | 2316 | 0.3303 | 0.6687 | 0.1717 | 0.6556 | 0.7464 | 0.6980 | 0.7670 | 0.8693 | 0.1018 |
| suspicious_action_sequence | 463 | 0.3305 | 0.9521 | 0.2313 | 0.9858 | 0.9085 | 0.9456 | 0.9701 | 0.9807 | 0.0067 |
| insufficient_context | 2321 | 0.0689 | 0.8610 | 0.7554 | 0.9837 | 0.7562 | 0.8551 | 0.9099 | 0.9894 | 0.0181 |

## Macro / worst slice

- macro `precision` = 0.9747
- macro `recall` = 0.9030
- macro `f1` = 0.9349
- macro `f1@selected` = 0.9360
- macro `auprc` = 0.9447
- macro `auroc` = 0.9745
- macro `brier` = 0.0202
- macro `ece` = 0.0131
- worst-slice `precision` = 0.1000 (contrastive_axis=instruction_provenance)
- worst-slice `recall` = 0.1000 (contrastive_axis=instruction_provenance)
- worst-slice `f1` = 0.1000 (contrastive_axis=instruction_provenance)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.6111 (contrastive_axis=instruction_provenance)
- worst-slice `auroc` = 0.6667 (contrastive_axis=instruction_provenance)
- worst-slice `brier` = 0.0004 (contrastive_axis=read_versus_write)
- worst-slice `ece` = 0.0077 (contrastive_axis=read_versus_write)

## Consistency
- pair consistency: 0.8750 over 32 directional pairs
- counterfactual sensitivity (mean |dp|): 0.8539
- surface-paraphrase invariance (mean |dp|): 0.0051, fraction moved: 0.4000
