# forecheck evaluation report — SYNTHETIC_IN_DISTRIBUTION

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=test, n=4967, sha256=15445b48048117c634ce5f34bfa97caa91a226493aad0f330712ea788f52fde0
Seed: 0. Generated at: 2026-09-21T22:22:14.878163+00:00.
Model: encoder/ibm-granite/granite-embedding-english-r2
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: test.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 4967 | 0.0787 | 0.8494 | 0.9928 | 1.0000 | 0.7647 | 0.8667 | 0.8135 | 0.8843 | 0.0164 |
| unauthorized_scope | 4720 | 0.1201 | 0.9851 | 0.9349 | 0.9946 | 0.9788 | 0.9867 | 0.9991 | 0.9998 | 0.0027 |
| sensitive_data_exposure | 1186 | 0.2201 | 0.9774 | 0.6785 | 0.9735 | 0.9847 | 0.9790 | 0.9990 | 0.9997 | 0.0067 |
| untrusted_destination | 1519 | 0.3641 | 0.9927 | 0.2476 | 0.9963 | 0.9855 | 0.9909 | 0.9940 | 0.9928 | 0.0095 |
| privilege_escalation | 4967 | 0.0193 | 0.6019 | 0.8665 | 0.4469 | 0.8333 | 0.5818 | 0.4946 | 0.9892 | 0.0375 |
| destructive_or_irreversible_action | 4967 | 0.1075 | 0.9723 | 0.9686 | 0.9942 | 0.9700 | 0.9820 | 0.9970 | 0.9995 | 0.0065 |
| financial_commitment | 4967 | 0.0797 | 1.0000 | 0.9060 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0017 |
| external_communication | 112 | 0.4911 | 1.0000 | 0.7287 | 1.0000 | 0.9818 | 0.9908 | 1.0000 | 1.0000 | 0.0372 |
| policy_conflict | 1364 | 0.3270 | 0.4936 | 0.4435 | 0.3402 | 0.9664 | 0.5032 | 0.4334 | 0.6264 | 0.1847 |
| suspicious_action_sequence | 1068 | 0.3099 | 0.7434 | 0.6604 | 0.8640 | 0.7100 | 0.7794 | 0.8707 | 0.9020 | 0.0845 |
| insufficient_context | 4967 | 0.0928 | 0.6153 | 0.8142 | 0.5850 | 0.6790 | 0.6285 | 0.6673 | 0.9001 | 0.1240 |

## Macro / worst slice

- macro `precision` = 0.8106
- macro `recall` = 0.9016
- macro `f1` = 0.8392
- macro `f1@selected` = 0.8445
- macro `auprc` = 0.8426
- macro `auroc` = 0.9358
- macro `brier` = 0.0462
- macro `ece` = 0.0465
- worst-slice `precision` = 0.3667 (contrastive_axis=policy_present_versus_absent)
- worst-slice `recall` = 0.4500 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1` = 0.3900 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.7335 (contrastive_axis=known_versus_lookalike_destination)
- worst-slice `auroc` = 0.8127 (contrastive_axis=known_versus_lookalike_destination)
- worst-slice `brier` = 0.0337 (contrastive_axis=policy_present_versus_absent)
- worst-slice `ece` = 0.0412 (trajectory_length=0)

## Consistency
- pair consistency: 0.9709 over 172 directional pairs
- counterfactual sensitivity (mean |dp|): 0.8885
- surface-paraphrase invariance (mean |dp|): 0.0236, fraction moved: 0.8400
