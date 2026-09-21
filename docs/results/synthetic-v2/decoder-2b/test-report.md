# forecheck evaluation report — SYNTHETIC_IN_DISTRIBUTION

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=test, n=4967, sha256=15445b48048117c634ce5f34bfa97caa91a226493aad0f330712ea788f52fde0
Seed: 0. Generated at: 2026-09-21T22:30:15.932259+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: test.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 4967 | 0.0787 | 0.8642 | 0.9999 | 1.0000 | 0.7621 | 0.8650 | 0.8008 | 0.8992 | 0.0031 |
| unauthorized_scope | 4720 | 0.1201 | 1.0000 | 0.9981 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| sensitive_data_exposure | 1186 | 0.2201 | 1.0000 | 0.9997 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| untrusted_destination | 1519 | 0.3641 | 0.9973 | 0.9865 | 0.9982 | 0.9964 | 0.9973 | 0.9994 | 0.9997 | 0.0015 |
| privilege_escalation | 4967 | 0.0193 | 0.5251 | 0.2344 | 0.4332 | 0.9792 | 0.6006 | 0.5260 | 0.9902 | 0.0032 |
| destructive_or_irreversible_action | 4967 | 0.1075 | 0.9915 | 0.9994 | 1.0000 | 0.9794 | 0.9896 | 0.9954 | 0.9995 | 0.0014 |
| financial_commitment | 4967 | 0.0797 | 1.0000 | 0.9993 | 1.0000 | 0.9975 | 0.9987 | 1.0000 | 1.0000 | 0.0000 |
| external_communication | 112 | 0.4911 | 1.0000 | 0.9997 | 1.0000 | 0.9818 | 0.9908 | 1.0000 | 1.0000 | 0.0005 |
| policy_conflict | 1364 | 0.3270 | 0.9921 | 0.9852 | 1.0000 | 0.9776 | 0.9887 | 0.9988 | 0.9994 | 0.0053 |
| suspicious_action_sequence | 1068 | 0.3099 | 0.9391 | 0.3309 | 0.9966 | 0.8852 | 0.9376 | 0.9659 | 0.9819 | 0.0055 |
| insufficient_context | 4967 | 0.0928 | 0.8101 | 0.3241 | 0.9395 | 0.7072 | 0.8069 | 0.8147 | 0.9216 | 0.0045 |

## Macro / worst slice

- macro `precision` = 0.9562
- macro `recall` = 0.8914
- macro `f1` = 0.9199
- macro `f1@selected` = 0.9250
- macro `auprc` = 0.9183
- macro `auroc` = 0.9810
- macro `brier` = 0.0087
- macro `ece` = 0.0023
- worst-slice `precision` = 0.5000 (contrastive_axis=policy_present_versus_absent)
- worst-slice `recall` = 0.4500 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1` = 0.4667 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.7879 (contrastive_axis=permission_versus_escalation)
- worst-slice `auroc` = 0.9107 (contrastive_axis=permission_versus_escalation)
- worst-slice `brier` = 0.0029 (contrastive_axis=surface_paraphrase)
- worst-slice `ece` = 0.0016 (trajectory_length=0)

## Consistency
- pair consistency: 0.9651 over 172 directional pairs
- counterfactual sensitivity (mean |dp|): 0.9270
- surface-paraphrase invariance (mean |dp|): 0.0025, fraction moved: 0.0000
