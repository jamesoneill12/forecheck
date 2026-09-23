# forecheck evaluation report — EXTERNAL_OR_HUMAN

Dataset: split=None, n=30143, sha256=138cef73d6b5bee120ebe48f5317290d93e25867dcd22740865e5037fd2d162a
Seed: 0. Generated at: 2026-09-23T02:52:15.713472+00:00.
Model: huggingface/ibm-granite/granite-3.3-8b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: None.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 29380 | 0.0985 | 0.4010 | n/a | n/a | n/a | n/a | 0.4902 | 0.8454 | 0.0501 |
| unauthorized_scope | 30143 | 0.2840 | 0.4768 | n/a | n/a | n/a | n/a | 0.3501 | 0.6149 | 0.5110 |
| sensitive_data_exposure | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| untrusted_destination | 2896 | 1.0000 | 0.6285 | n/a | n/a | n/a | n/a | n/a | n/a | 0.5414 |
| privilege_escalation | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| destructive_or_irreversible_action | 30143 | 0.0291 | 0.7698 | n/a | n/a | n/a | n/a | 0.9998 | 1.0000 | 0.0202 |
| financial_commitment | 30143 | 0.0537 | 0.8495 | n/a | n/a | n/a | n/a | 0.8402 | 0.9529 | 0.0131 |
| external_communication | 2737 | 1.0000 | 0.8988 | n/a | n/a | n/a | n/a | n/a | n/a | 0.1842 |
| policy_conflict | 30143 | 0.0749 | 0.5304 | n/a | n/a | n/a | n/a | 0.5397 | 0.9544 | 0.1540 |
| suspicious_action_sequence | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |
| insufficient_context | 0 | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a | n/a |

## Macro / worst slice

- macro `precision` = 0.7203
- macro `recall` = 0.7307
- macro `f1` = 0.6507
- macro `f1@selected` = n/a
- macro `auprc` = 0.6440
- macro `auroc` = 0.8735
- macro `brier` = 0.2034
- macro `ece` = 0.2106
- worst-slice `precision` = 0.2567 (trajectory_length=0)
- worst-slice `recall` = 0.3804 (trajectory_length=0)
- worst-slice `f1` = 0.2735 (trajectory_length=0)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.2649 (trajectory_length=0)
- worst-slice `auroc` = 0.6566 (trajectory_length=0)
- worst-slice `brier` = 0.1524 (trajectory_length=11+)
- worst-slice `ece` = 0.1668 (context_length=16k+)

## Consistency
- pair consistency: n/a over 0 directional pairs
- counterfactual sensitivity (mean |dp|): n/a
- surface-paraphrase invariance (mean |dp|): n/a, fraction moved: n/a
