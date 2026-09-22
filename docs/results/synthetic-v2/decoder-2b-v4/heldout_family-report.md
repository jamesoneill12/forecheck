# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_family, n=6653, sha256=66a28203a54adb40e602b3d56419fb2f07ab8e7fa2c462dcd8978f99f3dddc04
Seed: 0. Generated at: 2026-09-22T03:31:33.482412+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_family.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 6653 | 0.0824 | 0.8678 | 1.0000 | 1.0000 | 0.7628 | 0.8654 | 0.8035 | 0.8992 | 0.0018 |
| unauthorized_scope | 6335 | 0.1084 | 0.9993 | 0.0103 | 1.0000 | 0.9985 | 0.9993 | 0.9991 | 0.9997 | 0.0006 |
| sensitive_data_exposure | 1558 | 0.2080 | 1.0000 | 0.9996 | 1.0000 | 0.9907 | 0.9953 | 1.0000 | 1.0000 | 0.0000 |
| untrusted_destination | 2172 | 0.3568 | 0.9981 | 0.9899 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0009 |
| privilege_escalation | 6653 | 0.0708 | 1.0000 | 0.9996 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| destructive_or_irreversible_action | 6653 | 0.0875 | 0.9807 | 0.9950 | 1.0000 | 0.9622 | 0.9807 | 0.9917 | 0.9992 | 0.0011 |
| financial_commitment | 6653 | 0.0953 | 1.0000 | 1.0000 | 1.0000 | 0.9968 | 0.9984 | 1.0000 | 1.0000 | 0.0000 |
| external_communication | 287 | 0.5226 | 1.0000 | 0.9998 | 1.0000 | 0.9867 | 0.9933 | 1.0000 | 1.0000 | 0.0002 |
| policy_conflict | 1834 | 0.3713 | 0.9084 | 0.7570 | 0.9713 | 0.8443 | 0.9034 | 0.9635 | 0.9686 | 0.0389 |
| suspicious_action_sequence | 1392 | 0.3168 | 0.9348 | 0.3869 | 1.0000 | 0.8776 | 0.9348 | 0.9658 | 0.9804 | 0.0118 |
| insufficient_context | 6653 | 0.0870 | 0.8067 | 0.4294 | 0.9121 | 0.7168 | 0.8027 | 0.8406 | 0.9307 | 0.0078 |

## Macro / worst slice

- macro `precision` = 0.9915
- macro `recall` = 0.9242
- macro `f1` = 0.9542
- macro `f1@selected` = 0.9521
- macro `auprc` = 0.9604
- macro `auroc` = 0.9798
- macro `brier` = 0.0122
- macro `ece` = 0.0057
- worst-slice `precision` = 0.3636 (contrastive_axis=financial_materiality)
- worst-slice `recall` = 0.3636 (contrastive_axis=financial_materiality)
- worst-slice `f1` = 0.3636 (contrastive_axis=financial_materiality)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.8400 (contrastive_axis=financial_materiality)
- worst-slice `auroc` = 0.9193 (contrastive_axis=permission_versus_escalation)
- worst-slice `brier` = 0.0000 (contrastive_axis=instruction_provenance)
- worst-slice `ece` = 0.0016 (contrastive_axis=instruction_provenance)

## Consistency
- pair consistency: 0.9900 over 100 directional pairs
- counterfactual sensitivity (mean |dp|): 0.9620
- surface-paraphrase invariance (mean |dp|): 0.0092, fraction moved: 0.4545
