# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_family, n=6653, sha256=66a28203a54adb40e602b3d56419fb2f07ab8e7fa2c462dcd8978f99f3dddc04
Seed: 0. Generated at: 2026-09-22T03:43:58.353077+00:00.
Model: rule_baseline/rule-baseline-v1
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_family.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 6653 | 0.0824 | 0.4800 | 0.9500 | 0.3494 | 0.7664 | 0.4800 | 0.2870 | 0.8192 | 0.1302 |
| unauthorized_scope | 6335 | 0.1084 | 0.2702 | 0.9500 | 1.0000 | 0.4294 | 0.6008 | 0.5065 | 0.7244 | 0.1777 |
| sensitive_data_exposure | 1558 | 0.2080 | 0.6953 | 0.5000 | 0.5329 | 1.0000 | 0.6953 | 0.7515 | 0.9404 | 0.0702 |
| untrusted_destination | 2172 | 0.3568 | 1.0000 | 0.5000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0517 |
| privilege_escalation | 6653 | 0.0708 | 0.5629 | 0.9500 | 0.4292 | 0.8174 | 0.5629 | 0.3638 | 0.8673 | 0.1005 |
| destructive_or_irreversible_action | 6653 | 0.0875 | 0.9781 | 0.5000 | 1.0000 | 0.9570 | 0.9781 | 0.9608 | 0.9785 | 0.0494 |
| financial_commitment | 6653 | 0.0953 | 1.0000 | 0.9500 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0500 |
| external_communication | 287 | 0.5226 | 0.7752 | 0.9500 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.1864 |
| policy_conflict | 1834 | 0.3713 | 0.5371 | 0.0500 | 0.3713 | 1.0000 | 0.5416 | 0.3702 | 0.4977 | 0.1345 |
| suspicious_action_sequence | 1392 | 0.3168 | 0.4812 | 0.5000 | 0.3168 | 1.0000 | 0.4812 | 0.3177 | 0.5020 | 0.4095 |
| insufficient_context | 6653 | 0.0870 | 0.2742 | 0.9500 | 1.0000 | 0.1589 | 0.2742 | 0.2321 | 0.5794 | 0.0246 |

## Macro / worst slice

- macro `precision` = 0.6182
- macro `recall` = 0.8509
- macro `f1` = 0.6413
- macro `f1@selected` = 0.6922
- macro `auprc` = 0.6172
- macro `auroc` = 0.8099
- macro `brier` = 0.1146
- macro `ece` = 0.1259
- worst-slice `precision` = 0.1712 (contrastive_axis=financial_materiality)
- worst-slice `recall` = 0.3333 (context_length=1k-4k)
- worst-slice `f1` = 0.2147 (contrastive_axis=financial_materiality)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.4518 (contrastive_axis=financial_materiality)
- worst-slice `auroc` = 0.5000 (context_length=1k-4k)
- worst-slice `brier` = 0.0785 (trajectory_length=0)
- worst-slice `ece` = 0.0918 (trajectory_length=0)

## Consistency
- pair consistency: 0.6600 over 100 directional pairs
- counterfactual sensitivity (mean |dp|): 0.5409
- surface-paraphrase invariance (mean |dp|): 0.0000, fraction moved: 0.0000
