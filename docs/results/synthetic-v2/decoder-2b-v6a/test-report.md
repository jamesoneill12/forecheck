# forecheck evaluation report — SYNTHETIC_IN_DISTRIBUTION

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=test, n=4348, sha256=46881382bba378489506f747bea7c2173aae11c660e89b16cf1a172750bbfc9e
Seed: 0. Generated at: 2026-09-25T00:03:33.078950+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: test.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 4348 | 0.0911 | 0.8604 | 0.9998 | 1.0000 | 0.7551 | 0.8604 | 0.7941 | 0.8979 | 0.0059 |
| unauthorized_scope | 4146 | 0.1252 | 0.9990 | 0.4292 | 1.0000 | 0.9981 | 0.9990 | 0.9999 | 1.0000 | 0.0009 |
| sensitive_data_exposure | 1079 | 0.2039 | 1.0000 | 0.9981 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| untrusted_destination | 1385 | 0.3444 | 0.9979 | 0.9487 | 0.9958 | 0.9979 | 0.9969 | 0.9998 | 0.9999 | 0.0011 |
| privilege_escalation | 4348 | 0.0179 | 1.0000 | 0.9999 | 1.0000 | 0.9744 | 0.9870 | 1.0000 | 1.0000 | 0.0000 |
| destructive_or_irreversible_action | 4348 | 0.1083 | 0.9871 | 0.3689 | 1.0000 | 0.9745 | 0.9871 | 0.9950 | 0.9993 | 0.0016 |
| financial_commitment | 4348 | 0.0793 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| external_communication | 113 | 0.5310 | 1.0000 | 0.9859 | 1.0000 | 0.9500 | 0.9744 | 1.0000 | 1.0000 | 0.0011 |
| policy_conflict | 749 | 0.3031 | 0.9688 | 0.3462 | 0.9819 | 0.9559 | 0.9688 | 0.9937 | 0.9956 | 0.0136 |
| suspicious_action_sequence | 863 | 0.2654 | 0.9423 | 0.9561 | 1.0000 | 0.8908 | 0.9423 | 0.9645 | 0.9842 | 0.0121 |
| insufficient_context | 4348 | 0.0904 | 0.7988 | 0.8205 | 0.9925 | 0.6718 | 0.8012 | 0.7934 | 0.8983 | 0.0054 |

## Macro / worst slice

- macro `precision` = 0.9966
- macro `recall` = 0.9315
- macro `f1` = 0.9595
- macro `f1@selected` = 0.9561
- macro `auprc` = 0.9582
- macro `auroc` = 0.9796
- macro `brier` = 0.0085
- macro `ece` = 0.0038
- worst-slice `precision` = 0.4444 (contrastive_axis=policy_present_versus_absent)
- worst-slice `recall` = 0.4167 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1` = 0.4286 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.8558 (contrastive_axis=explicit_versus_inferred_intent)
- worst-slice `auroc` = 0.9081 (contrastive_axis=explicit_versus_inferred_intent)
- worst-slice `brier` = 0.0002 (context_length=1k-4k)
- worst-slice `ece` = 0.0038 (split=test)

## Consistency
- pair consistency: 0.9565 over 138 directional pairs
- counterfactual sensitivity (mean |dp|): 0.9425
- surface-paraphrase invariance (mean |dp|): 0.0035, fraction moved: 0.1500

## Approval elimination

Bundle `balanced`, n=4348, base incident rate=0.5522, incident rate mode=prefix. Ranking score: expected cost of ALLOW over the bundle's covered dimensions (destructive_or_irreversible_action, external_communication, financial_commitment, insufficient_context, policy_conflict, privilege_escalation, prompt_injection_influence, sensitive_data_exposure, suspicious_action_sequence, unauthorized_scope, untrusted_destination).

| budget | approvals eliminated | incident rate | review rate | deny rate |
|---|---|---|---|---|
| 0.100% | 0.0041 | 0.0000 | 0.7183 | 0.2776 |
| 0.500% | 0.0041 | 0.0000 | 0.7183 | 0.2776 |
| 1.000% | 0.0041 | 0.0000 | 0.7183 | 0.2776 |
| 2.000% | 0.0041 | 0.0000 | 0.7183 | 0.2776 |
| 5.000% | 0.2321 | 0.0496 | 0.4903 | 0.2776 |
