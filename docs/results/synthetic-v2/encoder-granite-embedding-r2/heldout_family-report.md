# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_family, n=6640, sha256=d9cc04a793e29537e02103993ac07731ff556a8429263537686fedd235f3f887
Seed: 0. Generated at: 2026-09-21T22:23:11.106769+00:00.
Model: encoder/ibm-granite/granite-embedding-english-r2
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_family.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 6640 | 0.0840 | 0.8124 | 0.9928 | 0.9977 | 0.7742 | 0.8718 | 0.8171 | 0.8820 | 0.0274 |
| unauthorized_scope | 6315 | 0.1123 | 0.9922 | 0.9349 | 0.9956 | 0.9647 | 0.9799 | 0.9992 | 0.9999 | 0.0017 |
| sensitive_data_exposure | 1540 | 0.2143 | 0.9865 | 0.6785 | 0.9880 | 0.9939 | 0.9909 | 0.9995 | 0.9999 | 0.0046 |
| untrusted_destination | 2109 | 0.3580 | 0.9967 | 0.2476 | 1.0000 | 0.9934 | 0.9967 | 0.9983 | 0.9986 | 0.0100 |
| privilege_escalation | 6640 | 0.0637 | 0.4836 | 0.8665 | 0.0000 | 0.0000 | 0.0000 | 0.4807 | 0.9377 | 0.0100 |
| destructive_or_irreversible_action | 6640 | 0.0907 | 0.8874 | 0.9686 | 0.9732 | 0.9668 | 0.9700 | 0.9861 | 0.9978 | 0.0234 |
| financial_commitment | 6640 | 0.0875 | 1.0000 | 0.9060 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0022 |
| external_communication | 284 | 0.5775 | 0.9939 | 0.7287 | 1.0000 | 0.9817 | 0.9908 | 1.0000 | 0.9999 | 0.0302 |
| policy_conflict | 1891 | 0.3178 | 0.4632 | 0.4435 | 0.3406 | 0.9101 | 0.4957 | 0.4168 | 0.5984 | 0.1887 |
| suspicious_action_sequence | 1289 | 0.3313 | 0.7298 | 0.6604 | 0.8010 | 0.7166 | 0.7565 | 0.8691 | 0.8970 | 0.0974 |
| insufficient_context | 6640 | 0.0861 | 0.5963 | 0.8142 | 0.5908 | 0.7168 | 0.6477 | 0.6792 | 0.9166 | 0.1444 |

## Macro / worst slice

- macro `precision` = 0.7892
- macro `recall` = 0.8552
- macro `f1` = 0.8129
- macro `f1@selected` = 0.7909
- macro `auprc` = 0.8405
- macro `auroc` = 0.9298
- macro `brier` = 0.0507
- macro `ece` = 0.0491
- worst-slice `precision` = 0.3636 (contrastive_axis=financial_materiality)
- worst-slice `recall` = 0.4545 (contrastive_axis=environment_stage)
- worst-slice `f1` = 0.3939 (contrastive_axis=financial_materiality)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.7697 (tool_family=payments_procurement)
- worst-slice `auroc` = 0.7500 (contrastive_axis=resource_sensitivity)
- worst-slice `brier` = 0.0297 (contrastive_axis=policy_present_versus_absent)
- worst-slice `ece` = 0.0378 (policy_absent)

## Consistency
- pair consistency: 0.9811 over 106 directional pairs
- counterfactual sensitivity (mean |dp|): 0.8808
- surface-paraphrase invariance (mean |dp|): 0.0370, fraction moved: 0.9091
