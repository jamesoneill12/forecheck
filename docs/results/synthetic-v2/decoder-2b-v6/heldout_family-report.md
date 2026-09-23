# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_family, n=6692, sha256=a46f88689d272734364dac7ae2b8a9c90053aaa7810bfa571cfbc6cf748940d1
Seed: 0. Generated at: 2026-09-23T03:55:06.226679+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_family.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 6692 | 0.0813 | 0.8586 | 0.9987 | 1.0000 | 0.7518 | 0.8583 | 0.7873 | 0.8990 | 0.0039 |
| unauthorized_scope | 6393 | 0.1215 | 0.9987 | 0.0074 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0010 |
| sensitive_data_exposure | 1521 | 0.2078 | 1.0000 | 0.9985 | 1.0000 | 0.9842 | 0.9920 | 1.0000 | 1.0000 | 0.0002 |
| untrusted_destination | 2102 | 0.3601 | 0.9987 | 0.9203 | 0.9974 | 0.9987 | 0.9980 | 1.0000 | 1.0000 | 0.0006 |
| privilege_escalation | 6692 | 0.0693 | 1.0000 | 0.9859 | 1.0000 | 0.9720 | 0.9858 | 1.0000 | 1.0000 | 0.0001 |
| destructive_or_irreversible_action | 6692 | 0.0867 | 0.9851 | 0.8436 | 1.0000 | 0.9707 | 0.9851 | 0.9937 | 0.9993 | 0.0011 |
| financial_commitment | 6692 | 0.0865 | 1.0000 | 0.9999 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| external_communication | 279 | 0.5054 | 1.0000 | 0.9981 | 1.0000 | 0.9433 | 0.9708 | 1.0000 | 1.0000 | 0.0008 |
| policy_conflict | 1894 | 0.3025 | 0.8576 | 0.1912 | 0.8217 | 0.8848 | 0.8521 | 0.9345 | 0.9661 | 0.0605 |
| suspicious_action_sequence | 1324 | 0.2938 | 0.9194 | 0.2848 | 0.9970 | 0.8509 | 0.9182 | 0.9507 | 0.9731 | 0.0105 |
| insufficient_context | 6692 | 0.0837 | 0.7940 | 0.9974 | 0.9973 | 0.6607 | 0.7948 | 0.7934 | 0.9085 | 0.0072 |

## Macro / worst slice

- macro `precision` = 0.9859
- macro `recall` = 0.9171
- macro `f1` = 0.9466
- macro `f1@selected` = 0.9414
- macro `auprc` = 0.9509
- macro `auroc` = 0.9769
- macro `brier` = 0.0147
- macro `ece` = 0.0078
- worst-slice `precision` = 0.4545 (contrastive_axis=environment_stage)
- worst-slice `recall` = 0.4091 (contrastive_axis=financial_materiality)
- worst-slice `f1` = 0.4242 (contrastive_axis=financial_materiality)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.8250 (contrastive_axis=environment_stage)
- worst-slice `auroc` = 0.9200 (contrastive_axis=environment_stage)
- worst-slice `brier` = 0.0003 (contrastive_axis=resource_sensitivity)
- worst-slice `ece` = 0.0064 (contrastive_axis=financial_materiality)

## Consistency
- pair consistency: 0.9615 over 104 directional pairs
- counterfactual sensitivity (mean |dp|): 0.9427
- surface-paraphrase invariance (mean |dp|): 0.0070, fraction moved: 0.3636

## Approval elimination

Bundle `balanced`, n=6692, base incident rate=0.5767, incident rate mode=prefix. Ranking score: expected cost of ALLOW over the bundle's covered dimensions (destructive_or_irreversible_action, external_communication, financial_commitment, insufficient_context, policy_conflict, privilege_escalation, prompt_injection_influence, sensitive_data_exposure, suspicious_action_sequence, unauthorized_scope, untrusted_destination).

| budget | approvals eliminated | incident rate | review rate | deny rate |
|---|---|---|---|---|
| 0.100% | 0.0021 | 0.0000 | 0.6996 | 0.2983 |
| 0.500% | 0.0021 | 0.0000 | 0.6996 | 0.2983 |
| 1.000% | 0.0021 | 0.0000 | 0.6996 | 0.2983 |
| 2.000% | 0.0021 | 0.0000 | 0.6996 | 0.2983 |
| 5.000% | 0.0269 | 0.0500 | 0.6748 | 0.2983 |
