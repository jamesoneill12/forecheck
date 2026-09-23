# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_family, n=6692, sha256=a46f88689d272734364dac7ae2b8a9c90053aaa7810bfa571cfbc6cf748940d1
Seed: 0. Generated at: 2026-09-23T05:37:40.245310+00:00.
Model: huggingface/ibm-granite/granite-3.3-8b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_family.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 6692 | 0.0813 | 0.8535 | 0.1079 | 1.0000 | 0.7500 | 0.8571 | 0.7899 | 0.9012 | 0.0044 |
| unauthorized_scope | 6393 | 0.1215 | 0.9968 | 0.0250 | 1.0000 | 0.9987 | 0.9994 | 0.9993 | 0.9998 | 0.0028 |
| sensitive_data_exposure | 1521 | 0.2078 | 1.0000 | 0.1192 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0002 |
| untrusted_destination | 2102 | 0.3601 | 0.9967 | 0.0517 | 0.9974 | 1.0000 | 0.9987 | 1.0000 | 1.0000 | 0.0027 |
| privilege_escalation | 6692 | 0.0693 | 1.0000 | 0.9948 | 1.0000 | 0.9978 | 0.9989 | 1.0000 | 1.0000 | 0.0000 |
| destructive_or_irreversible_action | 6692 | 0.0867 | 0.9825 | 0.1742 | 0.9877 | 0.9707 | 0.9791 | 0.9938 | 0.9993 | 0.0014 |
| financial_commitment | 6692 | 0.0865 | 0.9983 | 0.3775 | 1.0000 | 0.9965 | 0.9983 | 1.0000 | 1.0000 | 0.0004 |
| external_communication | 279 | 0.5054 | 1.0000 | 0.9988 | 1.0000 | 0.9787 | 0.9892 | 1.0000 | 1.0000 | 0.0015 |
| policy_conflict | 1894 | 0.3025 | 0.8850 | 0.1717 | 0.8471 | 0.9284 | 0.8859 | 0.9515 | 0.9768 | 0.0203 |
| suspicious_action_sequence | 1324 | 0.2938 | 0.9194 | 0.2313 | 0.9822 | 0.8509 | 0.9118 | 0.9457 | 0.9685 | 0.0091 |
| insufficient_context | 6692 | 0.0837 | 0.7855 | 0.7554 | 0.9790 | 0.6661 | 0.7928 | 0.7935 | 0.9014 | 0.0092 |

## Macro / worst slice

- macro `precision` = 0.9847
- macro `recall` = 0.9169
- macro `f1` = 0.9471
- macro `f1@selected` = 0.9465
- macro `auprc` = 0.9522
- macro `auroc` = 0.9770
- macro `brier` = 0.0131
- macro `ece` = 0.0047
- worst-slice `precision` = 0.4545 (contrastive_axis=environment_stage)
- worst-slice `recall` = 0.4091 (contrastive_axis=financial_materiality)
- worst-slice `f1` = 0.4242 (contrastive_axis=financial_materiality)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.8400 (contrastive_axis=environment_stage)
- worst-slice `auroc` = 0.9233 (contrastive_axis=financial_materiality)
- worst-slice `brier` = 0.0003 (contrastive_axis=resource_sensitivity)
- worst-slice `ece` = 0.0047 (split=heldout_family)

## Consistency
- pair consistency: 0.9712 over 104 directional pairs
- counterfactual sensitivity (mean |dp|): 0.9532
- surface-paraphrase invariance (mean |dp|): 0.0037, fraction moved: 0.1818

## Approval elimination

Bundle `balanced`, n=6692, base incident rate=0.5767, incident rate mode=prefix. Ranking score: expected cost of ALLOW over the bundle's covered dimensions (destructive_or_irreversible_action, external_communication, financial_commitment, insufficient_context, policy_conflict, privilege_escalation, prompt_injection_influence, sensitive_data_exposure, suspicious_action_sequence, unauthorized_scope, untrusted_destination).

| budget | approvals eliminated | incident rate | review rate | deny rate |
|---|---|---|---|---|
| 0.100% | 0.0054 | 0.0000 | 0.6996 | 0.2950 |
| 0.500% | 0.0054 | 0.0000 | 0.6996 | 0.2950 |
| 1.000% | 0.0054 | 0.0000 | 0.6996 | 0.2950 |
| 2.000% | 0.0054 | 0.0000 | 0.6996 | 0.2950 |
| 5.000% | 0.1082 | 0.0497 | 0.5968 | 0.2950 |
