# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_policy_phrasing, n=3294, sha256=b0f0bf6d553662bd5878707ee3f5ad245568f22e691bf4ba2593e1738f1d9020
Seed: 0. Generated at: 2026-09-21T23:24:32.966094+00:00.
Model: encoder/ibm-granite/granite-embedding-english-r2
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_policy_phrasing.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 3294 | 0.0808 | 0.8233 | 0.9963 | 1.0000 | 0.7143 | 0.8333 | 0.7641 | 0.8457 | 0.0133 |
| unauthorized_scope | 3148 | 0.1134 | 0.9819 | 0.5876 | 0.9804 | 0.9832 | 0.9818 | 0.9990 | 0.9999 | 0.0041 |
| sensitive_data_exposure | 786 | 0.2099 | 0.9610 | 0.7769 | 0.9874 | 0.9515 | 0.9691 | 0.9959 | 0.9989 | 0.0108 |
| untrusted_destination | 1021 | 0.3310 | 0.9896 | 0.7567 | 1.0000 | 0.9793 | 0.9895 | 0.9912 | 0.9887 | 0.0128 |
| privilege_escalation | 3294 | 0.0197 | 0.5926 | 0.7905 | 0.4101 | 0.8769 | 0.5588 | 0.4596 | 0.9864 | 0.0385 |
| destructive_or_irreversible_action | 3294 | 0.1078 | 0.9748 | 0.8861 | 0.9884 | 0.9634 | 0.9757 | 0.9959 | 0.9992 | 0.0046 |
| financial_commitment | 3294 | 0.0771 | 1.0000 | 0.9173 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0021 |
| external_communication | 57 | 0.4561 | 1.0000 | 0.5137 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0871 |
| policy_conflict | 3289 | 0.4092 | 0.4669 | 0.3797 | 0.4092 | 1.0000 | 0.5808 | 0.4644 | 0.5533 | 0.0858 |
| suspicious_action_sequence | 718 | 0.3008 | 0.7028 | 0.5983 | 0.7500 | 0.6944 | 0.7212 | 0.8235 | 0.8750 | 0.0965 |
| insufficient_context | 3294 | 0.0723 | 0.6410 | 0.7384 | 0.5628 | 0.9034 | 0.6935 | 0.6573 | 0.9657 | 0.1440 |

## Macro / worst slice

- macro `precision` = 0.8083
- macro `recall` = 0.8900
- macro `f1` = 0.8303
- macro `f1@selected` = 0.8458
- macro `auprc` = 0.8319
- macro `auroc` = 0.9284
- macro `brier` = 0.0494
- macro `ece` = 0.0454
- worst-slice `precision` = 0.1111 (contrastive_axis=permission_versus_escalation)
- worst-slice `recall` = 0.1111 (contrastive_axis=permission_versus_escalation)
- worst-slice `f1` = 0.1111 (contrastive_axis=permission_versus_escalation)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.7333 (contrastive_axis=financial_materiality)
- worst-slice `auroc` = 0.6667 (contrastive_axis=financial_materiality)
- worst-slice `brier` = 0.0173 (contrastive_axis=policy_present_versus_absent)
- worst-slice `ece` = 0.0357 (tool_family=crm_support)

## Consistency
- pair consistency: 0.9783 over 46 directional pairs
- counterfactual sensitivity (mean |dp|): 0.8385
- surface-paraphrase invariance (mean |dp|): 0.0253, fraction moved: 0.7778
