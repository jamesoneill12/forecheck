# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_policy_kind, n=2321, sha256=3bab4f82dfec3ac0d94f219b741e75f7918cde678fd5c7f2634ad9a02b14471f
Seed: 0. Generated at: 2026-09-25T00:21:25.538726+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_policy_kind.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 2321 | 0.0840 | 0.8496 | 0.9998 | 1.0000 | 0.7385 | 0.8496 | 0.7753 | 0.8817 | 0.0063 |
| unauthorized_scope | 2228 | 0.1095 | 1.0000 | 0.4292 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0010 |
| sensitive_data_exposure | 561 | 0.2103 | 0.9958 | 0.9981 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0016 |
| untrusted_destination | 704 | 0.3494 | 1.0000 | 0.9487 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0007 |
| privilege_escalation | 2321 | 0.0164 | 0.9867 | 0.9999 | 1.0000 | 0.9737 | 0.9867 | 0.9756 | 0.9952 | 0.0004 |
| destructive_or_irreversible_action | 2321 | 0.1004 | 0.9847 | 0.3689 | 1.0000 | 0.9700 | 0.9847 | 0.9953 | 0.9994 | 0.0018 |
| financial_commitment | 2321 | 0.0681 | 1.0000 | 1.0000 | 1.0000 | 0.9937 | 0.9968 | 1.0000 | 1.0000 | 0.0000 |
| external_communication | 54 | 0.6296 | 0.9851 | 0.9859 | 1.0000 | 0.9412 | 0.9697 | 1.0000 | 1.0000 | 0.0115 |
| policy_conflict | 2316 | 0.3303 | 0.6387 | 0.3462 | 0.6390 | 0.6248 | 0.6319 | 0.6952 | 0.7655 | 0.1701 |
| suspicious_action_sequence | 463 | 0.3305 | 0.9521 | 0.9561 | 1.0000 | 0.9085 | 0.9521 | 0.9717 | 0.9833 | 0.0050 |
| insufficient_context | 2321 | 0.0689 | 0.9267 | 0.8205 | 1.0000 | 0.8625 | 0.9262 | 0.9646 | 0.9964 | 0.0201 |

## Macro / worst slice

- macro `precision` = 0.9690
- macro `recall` = 0.9124
- macro `f1` = 0.9381
- macro `f1@selected` = 0.9361
- macro `auprc` = 0.9434
- macro `auroc` = 0.9656
- macro `brier` = 0.0241
- macro `ece` = 0.0199
- worst-slice `precision` = 0.1000 (contrastive_axis=instruction_provenance)
- worst-slice `recall` = 0.1000 (contrastive_axis=instruction_provenance)
- worst-slice `f1` = 0.1000 (contrastive_axis=instruction_provenance)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.6250 (contrastive_axis=policy_present_versus_absent)
- worst-slice `auroc` = 0.6667 (contrastive_axis=instruction_provenance)
- worst-slice `brier` = 0.0002 (contrastive_axis=reversibility)
- worst-slice `ece` = 0.0075 (contrastive_axis=resource_sensitivity)

## Consistency
- pair consistency: 0.9062 over 32 directional pairs
- counterfactual sensitivity (mean |dp|): 0.8540
- surface-paraphrase invariance (mean |dp|): 0.0033, fraction moved: 0.2000
