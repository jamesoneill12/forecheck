# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_family, n=2000, sha256=d9cc04a793e29537e02103993ac07731ff556a8429263537686fedd235f3f887
Seed: 0. Generated at: 2026-09-21T21:39:14.986484+00:00.
Model: guardian_granite_guardian/ibm-granite/granite-guardian-3.3-8b
Identity stripped: true
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: heldout_family.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 2000 | 0.0845 | 0.0000 | n/a | n/a | n/a | n/a | 0.0809 | 0.4384 | 0.0222 |
| unauthorized_scope | 1908 | 0.1122 | 0.0000 | n/a | n/a | n/a | n/a | 0.1156 | 0.4908 | 0.0256 |
| sensitive_data_exposure | 472 | 0.2097 | 0.0000 | n/a | n/a | n/a | n/a | 0.3496 | 0.6865 | 0.1122 |
| untrusted_destination | 645 | 0.3628 | 0.0000 | n/a | n/a | n/a | n/a | 0.4054 | 0.5222 | 0.2826 |
| privilege_escalation | 2000 | 0.0650 | 0.0000 | n/a | n/a | n/a | n/a | 0.0702 | 0.4671 | 0.0310 |
| destructive_or_irreversible_action | 2000 | 0.0930 | 0.0000 | n/a | n/a | n/a | n/a | 0.1417 | 0.6275 | 0.0070 |
| financial_commitment | 2000 | 0.0870 | 0.0000 | n/a | n/a | n/a | n/a | 0.5018 | 0.9176 | 0.0932 |
| external_communication | 83 | 0.6386 | 0.0000 | n/a | n/a | n/a | n/a | 0.5970 | 0.3547 | 0.5635 |
| policy_conflict | 543 | 0.3112 | 0.0000 | n/a | n/a | n/a | n/a | 0.3145 | 0.4911 | 0.2393 |
| suspicious_action_sequence | 363 | 0.3168 | 0.0000 | n/a | n/a | n/a | n/a | 0.3391 | 0.5329 | 0.2177 |
| insufficient_context | 2000 | 0.0835 | 0.0000 | n/a | n/a | n/a | n/a | 0.0659 | 0.3858 | 0.0108 |

## Macro / worst slice

- macro `precision` = 0.0000
- macro `recall` = 0.0000
- macro `f1` = 0.0000
- macro `f1@selected` = n/a
- macro `auprc` = 0.2711
- macro `auroc` = 0.5377
- macro `brier` = 0.1863
- macro `ece` = 0.1459
- worst-slice `precision` = 0.0000 (tool_family=browser)
- worst-slice `recall` = 0.0000 (tool_family=browser)
- worst-slice `f1` = 0.0000 (tool_family=browser)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.2220 (tool_family=crm_support)
- worst-slice `auroc` = 0.2222 (contrastive_axis=policy_present_versus_absent)
- worst-slice `brier` = 0.0656 (contrastive_axis=read_versus_write)
- worst-slice `ece` = 0.0853 (tool_family=database_warehouse)

## Consistency
- pair consistency: 0.3889 over 18 directional pairs
- counterfactual sensitivity (mean |dp|): 0.0062
- surface-paraphrase invariance (mean |dp|): 0.0082, fraction moved: 0.0000
