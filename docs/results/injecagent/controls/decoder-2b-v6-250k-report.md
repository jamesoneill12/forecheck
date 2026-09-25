# forecheck evaluation report — EXTERNAL_OR_HUMAN

Dataset: split=None, n=7446, sha256=f214f45d9e1204ad8732453752049921476235af57ec4c5ae648d829ca642631
Seed: 0. Generated at: 2026-09-25T12:10:49.392354+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: None.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 6392 | 0.2500 | 0.4870 | n/a | n/a | n/a | n/a | 0.3528 | 0.7096 | 0.2534 |
| unauthorized_scope | 7446 | 0.8584 | 0.0000 | n/a | n/a | n/a | n/a | 0.8524 | 0.4583 | 0.8311 |
| sensitive_data_exposure | 2176 | 1.0000 | 1.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 0.0000 |
| untrusted_destination | 2850 | 1.0000 | 0.9499 | n/a | n/a | n/a | n/a | n/a | n/a | 0.1033 |
| privilege_escalation | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| destructive_or_irreversible_action | 7446 | 0.1644 | 0.8580 | n/a | n/a | n/a | n/a | 0.8642 | 0.9887 | 0.0521 |
| financial_commitment | 7446 | 0.0548 | 1.0000 | n/a | n/a | n/a | n/a | 1.0000 | 1.0000 | 0.0000 |
| external_communication | 2380 | 1.0000 | 0.9998 | n/a | n/a | n/a | n/a | n/a | n/a | 0.0015 |
| policy_conflict | 7446 | 0.5297 | 0.0000 | n/a | n/a | n/a | n/a | 0.9100 | 0.9387 | 0.5213 |
| suspicious_action_sequence | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| insufficient_context | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Macro / worst slice

- macro `precision` = 0.6464
- macro `recall` = 0.6855
- macro `f1` = 0.6618
- macro `f1@selected` = n/a
- macro `auprc` = 0.7959
- macro `auroc` = 0.8191
- macro `brier` = 0.2178
- macro `ece` = 0.2203
- worst-slice `precision` = 0.0000 (tool_family=crm_support)
- worst-slice `recall` = 0.0000 (tool_family=crm_support)
- worst-slice `f1` = 0.0000 (tool_family=crm_support)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.5518 (context_length=<1k)
- worst-slice `auroc` = 0.5839 (tool_family=browser)
- worst-slice `brier` = 0.0004 (difficulty=easy)
- worst-slice `ece` = 0.0085 (difficulty=easy)

## Consistency
- pair consistency: n/a over 0 directional pairs
- counterfactual sensitivity (mean |dp|): n/a
- surface-paraphrase invariance (mean |dp|): n/a, fraction moved: n/a
