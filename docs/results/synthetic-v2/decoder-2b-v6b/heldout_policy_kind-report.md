# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_policy_kind, n=2321, sha256=de1d84dd39bc8f733604474f4faac1f89c87deac9ae39a72e879724edfdaf963
Seed: 0. Generated at: 2026-09-25T00:40:58.055884+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_policy_kind.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 2321 | 0.0840 | 0.8496 | 1.0000 | 1.0000 | 0.7333 | 0.8462 | 0.7826 | 0.8906 | 0.0074 |
| unauthorized_scope | 2228 | 0.1095 | 1.0000 | 0.0017 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0013 |
| sensitive_data_exposure | 561 | 0.2103 | 1.0000 | 0.9993 | 1.0000 | 0.9576 | 0.9784 | 1.0000 | 1.0000 | 0.0002 |
| untrusted_destination | 704 | 0.3494 | 1.0000 | 0.7311 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0003 |
| privilege_escalation | 2321 | 0.0164 | 0.9867 | 0.9993 | 1.0000 | 0.9211 | 0.9589 | 0.9764 | 0.9962 | 0.0004 |
| destructive_or_irreversible_action | 2321 | 0.1004 | 0.9847 | 0.9990 | 1.0000 | 0.9614 | 0.9803 | 0.9938 | 0.9992 | 0.0019 |
| financial_commitment | 2321 | 0.0681 | 1.0000 | 1.0000 | 1.0000 | 0.9937 | 0.9968 | 1.0000 | 1.0000 | 0.0000 |
| external_communication | 54 | 0.6296 | 1.0000 | 0.9996 | 1.0000 | 0.9118 | 0.9538 | 1.0000 | 1.0000 | 0.0039 |
| policy_conflict | 2316 | 0.3303 | 0.5797 | 0.4513 | 0.4926 | 0.6954 | 0.5767 | 0.6776 | 0.7460 | 0.2550 |
| suspicious_action_sequence | 463 | 0.3305 | 0.9521 | 0.9823 | 1.0000 | 0.9085 | 0.9521 | 0.9741 | 0.9854 | 0.0091 |
| insufficient_context | 2321 | 0.0689 | 0.8652 | 0.9831 | 1.0000 | 0.7625 | 0.8652 | 0.9187 | 0.9909 | 0.0184 |

## Macro / worst slice

- macro `precision` = 0.9545
- macro `recall` = 0.9131
- macro `f1` = 0.9289
- macro `f1@selected` = 0.9189
- macro `auprc` = 0.9385
- macro `auroc` = 0.9644
- macro `brier` = 0.0299
- macro `ece` = 0.0271
- worst-slice `precision` = 0.1000 (contrastive_axis=instruction_provenance)
- worst-slice `recall` = 0.1000 (contrastive_axis=instruction_provenance)
- worst-slice `f1` = 0.1000 (contrastive_axis=instruction_provenance)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.6389 (contrastive_axis=principal_authorization)
- worst-slice `auroc` = 0.3333 (contrastive_axis=principal_authorization)
- worst-slice `brier` = 0.0009 (contrastive_axis=resource_sensitivity)
- worst-slice `ece` = 0.0083 (contrastive_axis=resource_sensitivity)

## Consistency
- pair consistency: 0.9062 over 32 directional pairs
- counterfactual sensitivity (mean |dp|): 0.8542
- surface-paraphrase invariance (mean |dp|): 0.0050, fraction moved: 0.2000
