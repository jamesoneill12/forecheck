# forecheck evaluation report — EXTERNAL_OR_HUMAN

Dataset: split=None, n=4215, sha256=cecb2969b63cc61c8b48b84d1cb33309b3f31e12b7d99a61aaf5fca215a6d3ff
Seed: 0. Generated at: 2026-09-22T19:43:31.999775+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: None.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 4133 | 0.1495 | 0.0000 | n/a | n/a | n/a | n/a | 0.1403 | 0.4531 | 0.1299 |
| unauthorized_scope | 4215 | 0.2534 | 0.0000 | n/a | n/a | n/a | n/a | 0.3017 | 0.5122 | 0.2041 |
| sensitive_data_exposure | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| untrusted_destination | 1447 | 1.0000 | 0.5737 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5825 |
| privilege_escalation | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| destructive_or_irreversible_action | 4215 | 0.0966 | 0.4417 | n/a | n/a | n/a | n/a | 1.0000 | 1.0000 | 0.2441 |
| financial_commitment | 4215 | 0.3433 | 0.9141 | n/a | n/a | n/a | n/a | 1.0000 | 1.0000 | 0.0543 |
| external_communication | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| policy_conflict | 4215 | 0.2370 | 0.7171 | n/a | n/a | n/a | n/a | 0.8598 | 0.9374 | 0.1177 |
| suspicious_action_sequence | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| insufficient_context | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Macro / worst slice

- macro `precision` = 0.4816
- macro `recall` = 0.5203
- macro `f1` = 0.4411
- macro `f1@selected` = n/a
- macro `auprc` = 0.6604
- macro `auroc` = 0.7805
- macro `brier` = 0.2254
- macro `ece` = 0.2221
- worst-slice `precision` = 0.2000 (trajectory_length=0)
- worst-slice `recall` = 0.2000 (trajectory_length=0)
- worst-slice `f1` = 0.2000 (trajectory_length=0)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.4490 (trajectory_length=0)
- worst-slice `auroc` = 0.7323 (context_length=<1k)
- worst-slice `brier` = 0.0229 (trajectory_length=0)
- worst-slice `ece` = 0.0368 (trajectory_length=0)

## Consistency
- pair consistency: n/a over 0 directional pairs
- counterfactual sensitivity (mean |dp|): n/a
- surface-paraphrase invariance (mean |dp|): n/a, fraction moved: n/a
