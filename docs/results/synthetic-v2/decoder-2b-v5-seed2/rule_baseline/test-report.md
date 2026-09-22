# forecheck evaluation report — SYNTHETIC_IN_DISTRIBUTION

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=test, n=4348, sha256=d99a98c166e3cf6bdb66e814124476f7654a7b4adcae6e05a34b9469d743f8f0
Seed: 0. Generated at: 2026-09-22T18:41:58.710672+00:00.
Model: rule_baseline/rule-baseline-v1
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: test.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 4348 | 0.0911 | 0.5089 | 0.9500 | 0.3838 | 0.7551 | 0.5089 | 0.3121 | 0.8168 | 0.1202 |
| unauthorized_scope | 4146 | 0.1252 | 0.3010 | 0.9500 | 1.0000 | 0.4239 | 0.5954 | 0.5118 | 0.7138 | 0.1692 |
| sensitive_data_exposure | 1079 | 0.2039 | 0.6940 | 0.5000 | 0.5314 | 1.0000 | 0.6940 | 0.7588 | 0.9433 | 0.0723 |
| untrusted_destination | 1385 | 0.3444 | 1.0000 | 0.5000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0519 |
| privilege_escalation | 4348 | 0.0179 | 0.5408 | 0.9500 | 0.4065 | 0.8077 | 0.5408 | 0.3317 | 0.8931 | 0.0641 |
| destructive_or_irreversible_action | 4348 | 0.1083 | 0.9135 | 0.5000 | 1.0000 | 0.8408 | 0.9135 | 0.8580 | 0.9204 | 0.0359 |
| financial_commitment | 4348 | 0.0793 | 1.0000 | 0.9500 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0500 |
| external_communication | 113 | 0.5310 | 0.7595 | 0.9500 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.2013 |
| policy_conflict | 749 | 0.3031 | 0.4657 | 0.0500 | 0.3031 | 1.0000 | 0.4652 | 0.3047 | 0.5039 | 0.1947 |
| suspicious_action_sequence | 863 | 0.2654 | 0.4194 | 0.5000 | 0.2654 | 1.0000 | 0.4194 | 0.2645 | 0.4978 | 0.4641 |
| insufficient_context | 4348 | 0.0904 | 0.2987 | 0.9500 | 1.0000 | 0.1756 | 0.2987 | 0.2501 | 0.5878 | 0.0261 |

## Macro / worst slice

- macro `precision` = 0.6091
- macro `recall` = 0.8374
- macro `f1` = 0.6274
- macro `f1@selected` = 0.6760
- macro `auprc` = 0.5992
- macro `auroc` = 0.8070
- macro `brier` = 0.1130
- macro `ece` = 0.1318
- worst-slice `precision` = 0.1636 (contrastive_axis=policy_present_versus_absent)
- worst-slice `recall` = 0.3000 (context_length=1k-4k)
- worst-slice `f1` = 0.1958 (contrastive_axis=policy_present_versus_absent)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.4764 (contrastive_axis=policy_present_versus_absent)
- worst-slice `auroc` = 0.5000 (context_length=1k-4k)
- worst-slice `brier` = 0.0751 (trajectory_length=0)
- worst-slice `ece` = 0.0912 (trajectory_length=0)

## Consistency
- pair consistency: 0.6377 over 138 directional pairs
- counterfactual sensitivity (mean |dp|): 0.5017
- surface-paraphrase invariance (mean |dp|): 0.0000, fraction moved: 0.0000
