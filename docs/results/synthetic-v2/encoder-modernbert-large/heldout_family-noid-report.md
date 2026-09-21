# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_family, n=6640, sha256=d9cc04a793e29537e02103993ac07731ff556a8429263537686fedd235f3f887
Seed: 0. Generated at: 2026-09-21T23:00:53.088854+00:00.
Model: encoder/answerdotai/ModernBERT-large
Identity stripped: true
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_family.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 6640 | 0.0840 | 0.8716 | 1.1484 | 1.0000 | 0.7688 | 0.8693 | 0.8181 | 0.8877 | 0.0002 |
| unauthorized_scope | 6315 | 0.1123 | 0.2019 | 0.7500 | 0.1123 | 1.0000 | 0.2019 | 0.1157 | 0.4965 | 0.0005 |
| sensitive_data_exposure | 1540 | 0.2143 | 0.8616 | 1.1094 | 0.9202 | 0.7333 | 0.8162 | 0.9280 | 0.9725 | 0.0088 |
| untrusted_destination | 2109 | 0.3580 | 0.9920 | -0.5469 | 0.9817 | 0.9974 | 0.9895 | 0.9998 | 0.9999 | 0.0024 |
| privilege_escalation | 6640 | 0.0637 | 0.3468 | 2.5938 | 0.5000 | 0.0047 | 0.0094 | 0.4473 | 0.9380 | 0.0040 |
| destructive_or_irreversible_action | 6640 | 0.0907 | 0.9146 | 0.8633 | 0.9108 | 0.9668 | 0.9380 | 0.9851 | 0.9955 | 0.0071 |
| financial_commitment | 6640 | 0.0875 | 1.0000 | 2.9844 | 1.0000 | 0.9948 | 0.9974 | 1.0000 | 1.0000 | n/a |
| external_communication | 284 | 0.5775 | 0.9000 | -0.1836 | 0.9739 | 0.9085 | 0.9401 | 0.9912 | 0.9879 | 0.0316 |
| policy_conflict | 1891 | 0.3178 | 0.0750 | -0.2734 | 0.3455 | 0.7903 | 0.4808 | 0.3759 | 0.5863 | 0.0821 |
| suspicious_action_sequence | 1289 | 0.3313 | 0.6030 | 0.3516 | 0.6622 | 0.5785 | 0.6175 | 0.7258 | 0.7956 | 0.0432 |
| insufficient_context | 6640 | 0.0861 | 0.1614 | 4.0000 | 0.8824 | 0.3147 | 0.4639 | 0.4410 | 0.6847 | 0.0695 |

## Macro / worst slice

- macro `precision` = 0.6903
- macro `recall` = 0.7426
- macro `f1` = 0.6298
- macro `f1@selected` = 0.6658
- macro `auprc` = 0.7116
- macro `auroc` = 0.8495
- macro `brier` = 24.6897
- macro `ece` = 0.0249
- worst-slice `precision` = 0.1979 (contrastive_axis=financial_materiality)
- worst-slice `recall` = 0.2727 (contrastive_axis=financial_materiality)
- worst-slice `f1` = 0.2091 (contrastive_axis=financial_materiality)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.6245 (tool_family=crm_support)
- worst-slice `auroc` = 0.6750 (contrastive_axis=resource_sensitivity)
- worst-slice `brier` = 12.0810 (contrastive_axis=financial_materiality)
- worst-slice `ece` = 0.0240 (trajectory_length=0)

## Consistency
- pair consistency: 0.8774 over 106 directional pairs
- counterfactual sensitivity (mean |dp|): 8.4471
- surface-paraphrase invariance (mean |dp|): 0.5786, fraction moved: 1.0000
