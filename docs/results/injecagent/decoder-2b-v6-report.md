# forecheck evaluation report — EXTERNAL_OR_HUMAN

Dataset: split=None, n=4250, sha256=6e62b0c164609c21b21b8b4c7ade34a596122893ce67e66ea2d169c7f7dd6126
Seed: 0. Generated at: 2026-09-23T12:32:22.467799+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: None.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 3196 | 0.5000 | 0.6972 | n/a | n/a | n/a | n/a | 0.8780 | 0.8652 | 0.2247 |
| unauthorized_scope | 4250 | 0.7520 | 0.6652 | n/a | n/a | n/a | n/a | 0.7037 | 0.3761 | 0.3349 |
| sensitive_data_exposure | 1088 | 1.0000 | 1.0000 | n/a | n/a | n/a | n/a | n/a | n/a | 0.0002 |
| untrusted_destination | 1456 | 1.0000 | 0.9510 | n/a | n/a | n/a | n/a | n/a | n/a | 0.0882 |
| privilege_escalation | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| destructive_or_irreversible_action | 4250 | 0.1440 | 0.9652 | n/a | n/a | n/a | n/a | 0.9976 | 0.9996 | 0.0108 |
| financial_commitment | 4250 | 0.0480 | 0.8000 | n/a | n/a | n/a | n/a | 0.9696 | 0.9985 | 0.0160 |
| external_communication | 1190 | 1.0000 | 0.9807 | n/a | n/a | n/a | n/a | n/a | n/a | 0.0331 |
| policy_conflict | 4250 | 0.4640 | 0.7580 | n/a | n/a | n/a | n/a | 0.9222 | 0.9137 | 0.1857 |
| suspicious_action_sequence | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| insufficient_context | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Macro / worst slice

- macro `precision` = 0.9294
- macro `recall` = 0.7991
- macro `f1` = 0.8522
- macro `f1@selected` = n/a
- macro `auprc` = 0.8942
- macro `auroc` = 0.8306
- macro `brier` = 0.1071
- macro `ece` = 0.1117
- worst-slice `precision` = 0.0000 (tool_family=crm_support)
- worst-slice `recall` = 0.0000 (tool_family=crm_support)
- worst-slice `f1` = 0.0000 (tool_family=crm_support)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.5995 (context_length=<1k)
- worst-slice `auroc` = 0.4523 (tool_family=browser)
- worst-slice `brier` = 0.0442 (tool_family=email_messaging)
- worst-slice `ece` = 0.0471 (tool_family=email_messaging)

## Consistency
- pair consistency: n/a over 0 directional pairs
- counterfactual sensitivity (mean |dp|): n/a
- surface-paraphrase invariance (mean |dp|): n/a, fraction moved: n/a
