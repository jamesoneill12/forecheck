# forecheck evaluation report — SYNTHETIC_IN_DISTRIBUTION

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=test, n=2000, sha256=15445b48048117c634ce5f34bfa97caa91a226493aad0f330712ea788f52fde0
Seed: 0. Generated at: 2026-09-21T21:16:58.007515+00:00.
Model: guardian_granite_guardian/ibm-granite/granite-guardian-3.3-8b
Identity stripped: true
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: n/a. Reported split: test.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 2000 | 0.0750 | 0.0000 | n/a | n/a | n/a | n/a | 0.0672 | 0.4384 | 0.0225 |
| unauthorized_scope | 1910 | 0.1173 | 0.0000 | n/a | n/a | n/a | n/a | 0.1239 | 0.5221 | 0.0306 |
| sensitive_data_exposure | 452 | 0.2257 | 0.0000 | n/a | n/a | n/a | n/a | 0.3092 | 0.6046 | 0.1280 |
| untrusted_destination | 591 | 0.3672 | 0.0000 | n/a | n/a | n/a | n/a | 0.4115 | 0.5121 | 0.2862 |
| privilege_escalation | 2000 | 0.0175 | 0.0000 | n/a | n/a | n/a | n/a | 0.0198 | 0.4250 | 0.0788 |
| destructive_or_irreversible_action | 2000 | 0.1105 | 0.0000 | n/a | n/a | n/a | n/a | 0.1650 | 0.6097 | 0.0257 |
| financial_commitment | 2000 | 0.0800 | 0.0000 | n/a | n/a | n/a | n/a | 0.4742 | 0.9119 | 0.0673 |
| external_communication | 58 | 0.5517 | 0.0000 | n/a | n/a | n/a | n/a | 0.4239 | 0.2392 | 0.4756 |
| policy_conflict | 571 | 0.3275 | 0.0000 | n/a | n/a | n/a | n/a | 0.3199 | 0.4888 | 0.2564 |
| suspicious_action_sequence | 428 | 0.3341 | 0.0000 | n/a | n/a | n/a | n/a | 0.3461 | 0.5088 | 0.2348 |
| insufficient_context | 2000 | 0.0930 | 0.0000 | n/a | n/a | n/a | n/a | 0.0798 | 0.3702 | 0.0154 |

## Macro / worst slice

- macro `precision` = 0.0000
- macro `recall` = 0.0000
- macro `f1` = 0.0000
- macro `f1@selected` = n/a
- macro `auprc` = 0.2491
- macro `auroc` = 0.5119
- macro `brier` = 0.1816
- macro `ece` = 0.1474
- worst-slice `precision` = 0.0000 (tool_family=browser)
- worst-slice `recall` = 0.0000 (tool_family=browser)
- worst-slice `f1` = 0.0000 (tool_family=browser)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.1690 (is_benign_hard_negative)
- worst-slice `auroc` = 0.3562 (contrastive_axis=financial_materiality)
- worst-slice `brier` = 0.0307 (contrastive_axis=policy_present_versus_absent)
- worst-slice `ece` = 0.0745 (contrastive_axis=policy_present_versus_absent)

## Consistency
- pair consistency: 0.3333 over 21 directional pairs
- counterfactual sensitivity (mean |dp|): 0.0070
- surface-paraphrase invariance (mean |dp|): 0.0048, fraction moved: 0.0000
