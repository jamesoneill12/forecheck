# forecheck evaluation report — EXTERNAL_OR_HUMAN

Dataset: split=None, n=2000, sha256=138cef73d6b5bee120ebe48f5317290d93e25867dcd22740865e5037fd2d162a
Seed: 0. Generated at: 2026-09-23T02:16:54.566096+00:00.
Model: guardian_granite_guardian/ibm-granite/granite-guardian-3.3-8b
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: None.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 1949 | 0.0965 | 0.0000 | n/a | n/a | n/a | n/a | 0.1162 | 0.5533 | 0.0208 |
| unauthorized_scope | 2000 | 0.2555 | 0.0038 | n/a | n/a | n/a | n/a | 0.3101 | 0.5699 | 0.1618 |
| sensitive_data_exposure | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| untrusted_destination | 201 | 1.0000 | 0.0099 | n/a | n/a | n/a | n/a | n/a | n/a | 0.9133 |
| privilege_escalation | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| destructive_or_irreversible_action | 2000 | 0.0315 | 0.0000 | n/a | n/a | n/a | n/a | 0.0691 | 0.7170 | 0.0575 |
| financial_commitment | 2000 | 0.0600 | 0.0000 | n/a | n/a | n/a | n/a | 0.0914 | 0.6387 | 0.0289 |
| external_communication | 189 | 1.0000 | 0.0105 | n/a | n/a | n/a | n/a | n/a | n/a | 0.9020 |
| policy_conflict | 2000 | 0.0720 | 0.0000 | n/a | n/a | n/a | n/a | 0.0725 | 0.4754 | 0.0316 |
| suspicious_action_sequence | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| insufficient_context | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Macro / worst slice

- macro `precision` = 0.3016
- macro `recall` = 0.0017
- macro `f1` = 0.0035
- macro `f1@selected` = n/a
- macro `auprc` = 0.1319
- macro `auroc` = 0.5909
- macro `brier` = 0.3038
- macro `ece` = 0.3023
- worst-slice `precision` = 0.0000 (tool_family=payments_procurement)
- worst-slice `recall` = 0.0000 (tool_family=payments_procurement)
- worst-slice `f1` = 0.0000 (tool_family=payments_procurement)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.0590 (tool_family=payments_procurement)
- worst-slice `auroc` = 0.2043 (trajectory_length=11+)
- worst-slice `brier` = 0.0480 (trajectory_length=0)
- worst-slice `ece` = 0.0926 (trajectory_length=0)

## Consistency
- pair consistency: n/a over 0 directional pairs
- counterfactual sensitivity (mean |dp|): n/a
- surface-paraphrase invariance (mean |dp|): n/a, fraction moved: n/a
