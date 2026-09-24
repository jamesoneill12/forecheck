# forecheck evaluation report — EXTERNAL_OR_HUMAN

Dataset: split=None, n=7446, sha256=f214f45d9e1204ad8732453752049921476235af57ec4c5ae648d829ca642631
Seed: 0. Generated at: 2026-09-24T21:28:49.583321+00:00.
Model: huggingface/ibm-granite/granite-3.3-8b-instruct
Identity stripped: true
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: None.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 6392 | 0.2500 | 0.7561 | n/a | n/a | n/a | n/a | 0.9079 | 0.9529 | 0.0083 |
| unauthorized_scope | 7446 | 0.8584 | 0.8795 | n/a | n/a | n/a | n/a | 0.9626 | 0.8167 | 0.0849 |
| sensitive_data_exposure | 2176 | 1.0000 | 0.9336 | n/a | n/a | n/a | n/a | n/a | n/a | 0.0227 |
| untrusted_destination | 2850 | 1.0000 | 0.9499 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| privilege_escalation | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| destructive_or_irreversible_action | 7446 | 0.1644 | 0.8346 | n/a | n/a | n/a | n/a | 0.9979 | 0.9997 | 0.0004 |
| financial_commitment | 7446 | 0.0548 | 0.7748 | n/a | n/a | n/a | n/a | 0.8367 | 0.9821 | 0.0004 |
| external_communication | 2380 | 1.0000 | 0.9994 | n/a | n/a | n/a | n/a | n/a | n/a | 0.0006 |
| policy_conflict | 7446 | 0.5297 | 0.8499 | n/a | n/a | n/a | n/a | 0.9677 | 0.9621 | 0.0130 |
| suspicious_action_sequence | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| insufficient_context | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Macro / worst slice

- macro `precision` = 0.9471
- macro `recall` = 0.8291
- macro `f1` = 0.8722
- macro `f1@selected` = n/a
- macro `auprc` = 0.9345
- macro `auroc` = 0.9427
- macro `brier` = 97.7156
- macro `ece` = 0.0186
- worst-slice `precision` = 0.0000 (tool_family=crm_support)
- worst-slice `recall` = 0.0000 (tool_family=crm_support)
- worst-slice `f1` = 0.0000 (tool_family=crm_support)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.6712 (tool_family=shell_code_exec)
- worst-slice `auroc` = 0.8091 (tool_family=shell_code_exec)
- worst-slice `brier` = 84.4643 (tool_family=email_messaging)
- worst-slice `ece` = 0.0151 (tool_family=email_messaging)

## Consistency
- pair consistency: n/a over 0 directional pairs
- counterfactual sensitivity (mean |dp|): n/a
- surface-paraphrase invariance (mean |dp|): n/a, fraction moved: n/a
