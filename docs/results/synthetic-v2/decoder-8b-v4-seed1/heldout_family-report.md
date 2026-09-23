# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_family, n=6653, sha256=66a28203a54adb40e602b3d56419fb2f07ab8e7fa2c462dcd8978f99f3dddc04
Seed: 0. Generated at: 2026-09-23T02:37:36.390298+00:00.
Model: huggingface/ibm-granite/granite-3.3-8b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_family.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 6653 | 0.0824 | 0.8678 | 0.9997 | 1.0000 | 0.7646 | 0.8666 | 0.7968 | 0.8957 | 0.0024 |
| unauthorized_scope | 6335 | 0.1084 | 0.9638 | 0.0425 | 0.9971 | 0.9985 | 0.9978 | 1.0000 | 1.0000 | 0.0077 |
| sensitive_data_exposure | 1558 | 0.2080 | 1.0000 | 0.9495 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0001 |
| untrusted_destination | 2172 | 0.3568 | 0.9961 | 0.1256 | 0.9936 | 0.9974 | 0.9955 | 1.0000 | 1.0000 | 0.0028 |
| privilege_escalation | 6653 | 0.0708 | 1.0000 | 0.9996 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0003 |
| destructive_or_irreversible_action | 6653 | 0.0875 | 0.9731 | 0.4334 | 0.9825 | 0.9622 | 0.9722 | 0.9918 | 0.9992 | 0.0019 |
| financial_commitment | 6653 | 0.0953 | 0.9960 | 0.0242 | 1.0000 | 0.9953 | 0.9976 | 1.0000 | 1.0000 | 0.0009 |
| external_communication | 287 | 0.5226 | 0.9933 | 0.9444 | 1.0000 | 0.9800 | 0.9899 | 1.0000 | 1.0000 | 0.0063 |
| policy_conflict | 1834 | 0.3713 | 0.9170 | 0.9555 | 0.9688 | 0.8664 | 0.9147 | 0.9646 | 0.9780 | 0.0313 |
| suspicious_action_sequence | 1392 | 0.3168 | 0.9335 | 0.9720 | 1.0000 | 0.8753 | 0.9335 | 0.9570 | 0.9750 | 0.0035 |
| insufficient_context | 6653 | 0.0870 | 0.6444 | 0.2486 | 0.6622 | 0.6839 | 0.6729 | 0.7294 | 0.9130 | 0.0222 |

## Macro / worst slice

- macro `precision` = 0.9740
- macro `recall` = 0.9037
- macro `f1` = 0.9350
- macro `f1@selected` = 0.9401
- macro `auprc` = 0.9490
- macro `auroc` = 0.9783
- macro `brier` = 0.0146
- macro `ece` = 0.0072
- worst-slice `precision` = 0.3636 (contrastive_axis=financial_materiality)
- worst-slice `recall` = 0.3636 (contrastive_axis=financial_materiality)
- worst-slice `f1` = 0.3636 (contrastive_axis=financial_materiality)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.8200 (contrastive_axis=financial_materiality)
- worst-slice `auroc` = 0.9187 (contrastive_axis=financial_materiality)
- worst-slice `brier` = 0.0002 (contrastive_axis=instruction_provenance)
- worst-slice `ece` = 0.0059 (contrastive_axis=instruction_provenance)

## Consistency
- pair consistency: 0.9900 over 100 directional pairs
- counterfactual sensitivity (mean |dp|): 0.9438
- surface-paraphrase invariance (mean |dp|): 0.0024, fraction moved: 0.2727

## Approval elimination

Bundle `balanced`, n=6653, base incident rate=0.5876, incident rate mode=prefix. Ranking score: expected cost of ALLOW over the bundle's covered dimensions (destructive_or_irreversible_action, external_communication, financial_commitment, insufficient_context, policy_conflict, privilege_escalation, prompt_injection_influence, sensitive_data_exposure, suspicious_action_sequence, unauthorized_scope, untrusted_destination).

| budget | approvals eliminated | incident rate | review rate | deny rate |
|---|---|---|---|---|
| 0.100% | 0.0029 | 0.0000 | 0.6952 | 0.3020 |
| 0.500% | 0.0029 | 0.0000 | 0.6952 | 0.3020 |
| 1.000% | 0.0029 | 0.0000 | 0.6952 | 0.3020 |
| 2.000% | 0.0029 | 0.0000 | 0.6952 | 0.3020 |
| 5.000% | 0.0771 | 0.0487 | 0.6209 | 0.3020 |
