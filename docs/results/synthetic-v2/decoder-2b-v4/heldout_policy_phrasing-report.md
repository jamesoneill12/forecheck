# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_policy_phrasing, n=3294, sha256=7fbe073090b3926e1a63466b386da1e8a1e85fc57458f4d6abbba730d1e8b8f6
Seed: 0. Generated at: 2026-09-22T03:43:23.009806+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_policy_phrasing.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 3294 | 0.0808 | 0.8359 | 1.0000 | 1.0000 | 0.7180 | 0.8359 | 0.7561 | 0.8709 | 0.0058 |
| unauthorized_scope | 3148 | 0.1134 | 1.0000 | 0.0103 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0007 |
| sensitive_data_exposure | 786 | 0.2099 | 1.0000 | 0.9996 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0001 |
| untrusted_destination | 1021 | 0.3310 | 0.9985 | 0.9899 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0016 |
| privilege_escalation | 3294 | 0.0197 | 0.9922 | 0.9996 | 1.0000 | 0.9846 | 0.9922 | 0.9889 | 0.9992 | 0.0003 |
| destructive_or_irreversible_action | 3294 | 0.1078 | 0.9886 | 0.9950 | 1.0000 | 0.9775 | 0.9886 | 0.9971 | 0.9997 | 0.0006 |
| financial_commitment | 3294 | 0.0771 | 1.0000 | 1.0000 | 1.0000 | 0.9921 | 0.9960 | 1.0000 | 1.0000 | 0.0000 |
| external_communication | 57 | 0.4561 | 1.0000 | 0.9998 | 1.0000 | 0.9231 | 0.9600 | 1.0000 | 1.0000 | 0.0000 |
| policy_conflict | 3289 | 0.4092 | 0.9555 | 0.7570 | 0.9927 | 0.9131 | 0.9512 | 0.9930 | 0.9943 | 0.0106 |
| suspicious_action_sequence | 718 | 0.3008 | 0.9231 | 0.3869 | 0.9947 | 0.8611 | 0.9231 | 0.9595 | 0.9766 | 0.0161 |
| insufficient_context | 3294 | 0.0723 | 0.8863 | 0.4294 | 0.9600 | 0.8067 | 0.8767 | 0.9516 | 0.9941 | 0.0156 |

## Macro / worst slice

- macro `precision` = 0.9965
- macro `recall` = 0.9342
- macro `f1` = 0.9618
- macro `f1@selected` = 0.9567
- macro `auprc` = 0.9678
- macro `auroc` = 0.9850
- macro `brier` = 0.0089
- macro `ece` = 0.0047
- worst-slice `precision` = 0.1111 (contrastive_axis=permission_versus_escalation)
- worst-slice `recall` = 0.1111 (contrastive_axis=permission_versus_escalation)
- worst-slice `f1` = 0.1111 (contrastive_axis=permission_versus_escalation)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.8472 (contrastive_axis=principal_authorization)
- worst-slice `auroc` = 0.9111 (contrastive_axis=principal_authorization)
- worst-slice `brier` = 0.0001 (contrastive_axis=policy_present_versus_absent)
- worst-slice `ece` = 0.0041 (trajectory_length=0)

## Consistency
- pair consistency: 0.9783 over 46 directional pairs
- counterfactual sensitivity (mean |dp|): 0.9460
- surface-paraphrase invariance (mean |dp|): 0.0034, fraction moved: 0.1111
