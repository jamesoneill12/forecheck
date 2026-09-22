# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_policy_phrasing, n=3294, sha256=7fbe073090b3926e1a63466b386da1e8a1e85fc57458f4d6abbba730d1e8b8f6
Seed: 0. Generated at: 2026-09-22T10:56:58.965453+00:00.
Model: encoder/ibm-granite/granite-embedding-english-r2
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_policy_phrasing.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 3294 | 0.0808 | 0.8059 | 0.9616 | 1.0000 | 0.7105 | 0.8308 | 0.7647 | 0.8478 | 0.0199 |
| unauthorized_scope | 3148 | 0.1134 | 0.9972 | 0.6378 | 0.9972 | 1.0000 | 0.9986 | 1.0000 | 1.0000 | 0.0026 |
| sensitive_data_exposure | 786 | 0.2099 | 0.9790 | 0.7762 | 0.9818 | 0.9818 | 0.9818 | 0.9974 | 0.9993 | 0.0137 |
| untrusted_destination | 1021 | 0.3310 | 0.9911 | 0.7960 | 1.0000 | 0.9822 | 0.9910 | 0.9905 | 0.9869 | 0.0094 |
| privilege_escalation | 3294 | 0.0197 | 0.5991 | 0.8238 | 0.4122 | 0.8308 | 0.5510 | 0.4518 | 0.9865 | 0.0401 |
| destructive_or_irreversible_action | 3294 | 0.1078 | 0.9747 | 0.8757 | 0.9913 | 0.9634 | 0.9771 | 0.9964 | 0.9994 | 0.0052 |
| financial_commitment | 3294 | 0.0771 | 1.0000 | 0.8233 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0021 |
| external_communication | 57 | 0.4561 | 1.0000 | 0.9863 | 1.0000 | 0.9615 | 0.9804 | 1.0000 | 1.0000 | 0.0012 |
| policy_conflict | 3289 | 0.4092 | 0.4836 | 0.4845 | 0.4086 | 0.9829 | 0.5772 | 0.4574 | 0.5483 | 0.0916 |
| suspicious_action_sequence | 718 | 0.3008 | 0.6951 | 0.6189 | 0.7350 | 0.6806 | 0.7067 | 0.8195 | 0.8649 | 0.1061 |
| insufficient_context | 3294 | 0.0723 | 0.6392 | 0.7596 | 0.5773 | 0.8782 | 0.6967 | 0.7281 | 0.9731 | 0.1396 |

## Macro / worst slice

- macro `precision` = 0.8043
- macro `recall` = 0.9004
- macro `f1` = 0.8332
- macro `f1@selected` = 0.8447
- macro `auprc` = 0.8369
- macro `auroc` = 0.9278
- macro `brier` = 0.0482
- macro `ece` = 0.0392
- worst-slice `precision` = 0.1111 (contrastive_axis=permission_versus_escalation)
- worst-slice `recall` = 0.1111 (contrastive_axis=permission_versus_escalation)
- worst-slice `f1` = 0.1111 (contrastive_axis=permission_versus_escalation)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.7333 (contrastive_axis=financial_materiality)
- worst-slice `auroc` = 0.6667 (contrastive_axis=financial_materiality)
- worst-slice `brier` = 0.0120 (contrastive_axis=policy_present_versus_absent)
- worst-slice `ece` = 0.0321 (trajectory_length=0)

## Consistency
- pair consistency: 0.9783 over 46 directional pairs
- counterfactual sensitivity (mean |dp|): 0.8935
- surface-paraphrase invariance (mean |dp|): 0.0335, fraction moved: 1.0000
