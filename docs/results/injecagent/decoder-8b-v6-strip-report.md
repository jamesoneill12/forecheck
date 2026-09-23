# forecheck evaluation report — EXTERNAL_OR_HUMAN

Dataset: split=None, n=4250, sha256=6e62b0c164609c21b21b8b4c7ade34a596122893ce67e66ea2d169c7f7dd6126
Seed: 0. Generated at: 2026-09-23T13:01:17.921094+00:00.
Model: huggingface/ibm-granite/granite-3.3-8b-instruct
Identity stripped: true
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: None.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 3196 | 0.5000 | 0.7578 | n/a | n/a | n/a | n/a | 0.9529 | 0.9493 | 0.0167 |
| unauthorized_scope | 4250 | 0.7520 | 0.8281 | n/a | n/a | n/a | n/a | 0.9173 | 0.7858 | 0.1025 |
| sensitive_data_exposure | 1088 | 1.0000 | 0.9286 | n/a | n/a | n/a | n/a | n/a | n/a | 0.0239 |
| untrusted_destination | 1456 | 1.0000 | 0.9510 | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| privilege_escalation | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| destructive_or_irreversible_action | 4250 | 0.1440 | 0.8355 | n/a | n/a | n/a | n/a | 0.9978 | 0.9997 | 0.0004 |
| financial_commitment | 4250 | 0.0480 | 0.7821 | n/a | n/a | n/a | n/a | 0.8386 | 0.9837 | 0.0005 |
| external_communication | 1190 | 1.0000 | 0.9987 | n/a | n/a | n/a | n/a | n/a | n/a | 0.0013 |
| policy_conflict | 4250 | 0.4640 | 0.8593 | n/a | n/a | n/a | n/a | 0.9631 | 0.9647 | 0.0124 |
| suspicious_action_sequence | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| insufficient_context | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Macro / worst slice

- macro `precision` = 0.9376
- macro `recall` = 0.8282
- macro `f1` = 0.8676
- macro `f1@selected` = n/a
- macro `auprc` = 0.9340
- macro `auroc` = 0.9366
- macro `brier` = 98.5770
- macro `ece` = 0.0225
- worst-slice `precision` = 0.0000 (tool_family=crm_support)
- worst-slice `recall` = 0.0000 (tool_family=crm_support)
- worst-slice `f1` = 0.0000 (tool_family=crm_support)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.7705 (context_length=<1k)
- worst-slice `auroc` = 0.8235 (tool_family=shell_code_exec)
- worst-slice `brier` = 88.5765 (tool_family=email_messaging)
- worst-slice `ece` = 0.0207 (tool_family=email_messaging)

## Consistency
- pair consistency: n/a over 0 directional pairs
- counterfactual sensitivity (mean |dp|): n/a
- surface-paraphrase invariance (mean |dp|): n/a, fraction moved: n/a
