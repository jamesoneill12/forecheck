# forecheck evaluation report — EXTERNAL_OR_HUMAN

Dataset: split=None, n=7446, sha256=f214f45d9e1204ad8732453752049921476235af57ec4c5ae648d829ca642631
Seed: 0. Generated at: 2026-09-25T12:18:31.498401+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: None.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 6392 | 0.2500 | 0.8138 | n/a | n/a | n/a | n/a | 0.8983 | 0.9309 | 0.0609 |
| unauthorized_scope | 7446 | 0.8584 | 0.8786 | n/a | n/a | n/a | n/a | 0.9439 | 0.7635 | 0.1523 |
| sensitive_data_exposure | 2176 | 1.0000 | 0.9993 | n/a | n/a | n/a | n/a | n/a | n/a | 0.0147 |
| untrusted_destination | 2850 | 1.0000 | 0.9499 | n/a | n/a | n/a | n/a | n/a | n/a | 0.0906 |
| privilege_escalation | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| destructive_or_irreversible_action | 7446 | 0.1644 | 0.7610 | n/a | n/a | n/a | n/a | 0.9982 | 0.9997 | 0.1303 |
| financial_commitment | 7446 | 0.0548 | 0.8157 | n/a | n/a | n/a | n/a | 0.9626 | 0.9967 | 0.0160 |
| external_communication | 2380 | 1.0000 | 0.9874 | n/a | n/a | n/a | n/a | n/a | n/a | 0.0297 |
| policy_conflict | 7446 | 0.5297 | 0.3692 | n/a | n/a | n/a | n/a | 0.9113 | 0.9129 | 0.3053 |
| suspicious_action_sequence | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| insufficient_context | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Macro / worst slice

- macro `precision` = 0.9124
- macro `recall` = 0.8108
- macro `f1` = 0.8219
- macro `f1@selected` = n/a
- macro `auprc` = 0.9429
- macro `auroc` = 0.9207
- macro `brier` = 0.0871
- macro `ece` = 0.1000
- worst-slice `precision` = 0.0000 (tool_family=crm_support)
- worst-slice `recall` = 0.0000 (tool_family=crm_support)
- worst-slice `f1` = 0.0000 (tool_family=crm_support)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.6856 (tool_family=shell_code_exec)
- worst-slice `auroc` = 0.7416 (tool_family=shell_code_exec)
- worst-slice `brier` = 0.0545 (tool_family=hr_identity)
- worst-slice `ece` = 0.0846 (tool_family=hr_identity)

## Consistency
- pair consistency: n/a over 0 directional pairs
- counterfactual sensitivity (mean |dp|): n/a
- surface-paraphrase invariance (mean |dp|): n/a, fraction moved: n/a
