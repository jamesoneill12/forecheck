# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_policy_kind, n=2321, sha256=6c927ac4ec27ba92e7d3f68a24e047d7c15da921f0a26b5f8a909f2ddef49776
Seed: 0. Generated at: 2026-09-22T13:38:39.526548+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_policy_kind.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 2321 | 0.0840 | 0.8547 | 0.9717 | 1.0000 | 0.7385 | 0.8496 | 0.7862 | 0.8990 | 0.0091 |
| unauthorized_scope | 2228 | 0.1095 | 1.0000 | 0.0070 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0012 |
| sensitive_data_exposure | 561 | 0.2103 | 1.0000 | 0.9993 | 1.0000 | 0.9915 | 0.9957 | 1.0000 | 1.0000 | 0.0000 |
| untrusted_destination | 704 | 0.3494 | 0.9980 | 0.5000 | 1.0000 | 0.9959 | 0.9980 | 1.0000 | 1.0000 | 0.0022 |
| privilege_escalation | 2321 | 0.0164 | 0.9867 | 1.0000 | 1.0000 | 0.9737 | 0.9867 | 0.9742 | 0.9783 | 0.0004 |
| destructive_or_irreversible_action | 2321 | 0.1004 | 0.9847 | 0.9427 | 1.0000 | 0.9700 | 0.9847 | 0.9947 | 0.9993 | 0.0018 |
| financial_commitment | 2321 | 0.0681 | 1.0000 | 0.9997 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| external_communication | 54 | 0.6296 | 0.9697 | 0.9999 | 1.0000 | 0.9412 | 0.9697 | 1.0000 | 1.0000 | 0.0296 |
| policy_conflict | 2316 | 0.3303 | 0.5612 | 0.5448 | 0.5446 | 0.5752 | 0.5594 | 0.7043 | 0.7731 | 0.2502 |
| suspicious_action_sequence | 463 | 0.3305 | 0.9521 | 0.9877 | 1.0000 | 0.9085 | 0.9521 | 0.9683 | 0.9815 | 0.0094 |
| insufficient_context | 2321 | 0.0689 | 0.8652 | 0.9393 | 1.0000 | 0.7562 | 0.8612 | 0.9189 | 0.9919 | 0.0171 |

## Macro / worst slice

- macro `precision` = 0.9571
- macro `recall` = 0.8988
- macro `f1` = 0.9247
- macro `f1@selected` = 0.9234
- macro `auprc` = 0.9406
- macro `auroc` = 0.9657
- macro `brier` = 0.0316
- macro `ece` = 0.0292
- worst-slice `precision` = 0.1000 (contrastive_axis=instruction_provenance)
- worst-slice `recall` = 0.1000 (contrastive_axis=instruction_provenance)
- worst-slice `f1` = 0.1000 (contrastive_axis=instruction_provenance)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.6111 (contrastive_axis=instruction_provenance)
- worst-slice `auroc` = 0.6667 (contrastive_axis=instruction_provenance)
- worst-slice `brier` = 0.0001 (contrastive_axis=read_versus_write)
- worst-slice `ece` = 0.0040 (contrastive_axis=read_versus_write)

## Consistency
- pair consistency: 0.9062 over 32 directional pairs
- counterfactual sensitivity (mean |dp|): 0.8602
- surface-paraphrase invariance (mean |dp|): 0.0018, fraction moved: 0.0000

## Approval elimination

Bundle `balanced`, n=2321, base incident rate=0.6497. Ranking score: expected cost of ALLOW over the bundle's covered dimensions (destructive_or_irreversible_action, external_communication, financial_commitment, insufficient_context, policy_conflict, privilege_escalation, prompt_injection_influence, sensitive_data_exposure, suspicious_action_sequence, unauthorized_scope, untrusted_destination).

| budget | approvals eliminated | incident rate | review rate | deny rate |
|---|---|---|---|---|
| 0.100% | 0.0017 | 0.0000 | 0.7441 | 0.2542 |
| 0.500% | 0.0017 | 0.0000 | 0.7441 | 0.2542 |
| 1.000% | 0.0017 | 0.0000 | 0.7441 | 0.2542 |
| 2.000% | 0.0017 | 0.0000 | 0.7441 | 0.2542 |
| 5.000% | 0.0017 | 0.0000 | 0.7441 | 0.2542 |
