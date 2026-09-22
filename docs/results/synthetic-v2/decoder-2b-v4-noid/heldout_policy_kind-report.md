# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_policy_kind, n=2247, sha256=99c768cce2dd5ac344288cf1ca35a2825ca52a9ea3002ff39d94f71c96406a2c
Seed: 0. Generated at: 2026-09-22T16:38:25.187148+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: true
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_policy_kind.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 2247 | 0.0757 | 0.8194 | 1.0000 | 1.0000 | 0.6941 | 0.8194 | 0.7246 | 0.8369 | 0.0004 |
| unauthorized_scope | 2139 | 0.1169 | 0.0000 | 0.1025 | 0.1173 | 1.0000 | 0.2099 | 0.1203 | 0.5116 | 0.0191 |
| sensitive_data_exposure | 510 | 0.2118 | 1.0000 | 0.9859 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0051 |
| untrusted_destination | 647 | 0.3215 | 0.9976 | 0.0525 | 1.0000 | 0.9952 | 0.9976 | 0.9971 | 0.9975 | 0.0023 |
| privilege_escalation | 2247 | 0.0191 | 1.0000 | 0.9988 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0015 |
| destructive_or_irreversible_action | 2247 | 0.0961 | 0.9835 | 0.4136 | 1.0000 | 0.9676 | 0.9835 | 0.9952 | 0.9994 | 0.0014 |
| financial_commitment | 2247 | 0.0797 | 1.0000 | 0.9996 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0001 |
| external_communication | 53 | 0.6226 | 1.0000 | 0.9997 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0146 |
| policy_conflict | 2247 | 0.4050 | 0.5765 | 0.5000 | 0.4050 | 1.0000 | 0.5765 | 0.4379 | 0.5531 | 0.2283 |
| suspicious_action_sequence | 460 | 0.3130 | 0.9451 | 1.0000 | 1.0000 | 0.8958 | 0.9451 | 0.9522 | 0.9678 | 0.0060 |
| insufficient_context | 2247 | 0.0788 | 0.4675 | 0.1731 | 0.9655 | 0.3164 | 0.4766 | 0.3823 | 0.6693 | 0.0132 |

## Macro / worst slice

- macro `precision` = 0.8550
- macro `recall` = 0.8053
- macro `f1` = 0.7991
- macro `f1@selected` = 0.8190
- macro `auprc` = 0.7827
- macro `auroc` = 0.8669
- macro `brier` = 0.0462
- macro `ece` = 0.0265
- worst-slice `precision` = 0.0000 (contrastive_axis=resource_sensitivity)
- worst-slice `recall` = 0.0000 (contrastive_axis=resource_sensitivity)
- worst-slice `f1` = 0.0000 (contrastive_axis=resource_sensitivity)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.2500 (contrastive_axis=resource_sensitivity)
- worst-slice `auroc` = 0.3333 (contrastive_axis=resource_sensitivity)
- worst-slice `brier` = 0.0229 (contrastive_axis=known_versus_lookalike_destination)
- worst-slice `ece` = 0.0229 (tool_family=hr_identity)

## Consistency
- pair consistency: 0.8387 over 31 directional pairs
- counterfactual sensitivity (mean |dp|): 0.7431
- surface-paraphrase invariance (mean |dp|): 0.0268, fraction moved: 0.8000

## Approval elimination

Bundle `balanced`, n=2247, base incident rate=0.7045, incident rate mode=prefix. Ranking score: expected cost of ALLOW over the bundle's covered dimensions (destructive_or_irreversible_action, external_communication, financial_commitment, insufficient_context, policy_conflict, privilege_escalation, prompt_injection_influence, sensitive_data_exposure, suspicious_action_sequence, unauthorized_scope, untrusted_destination).

| budget | approvals eliminated | incident rate | review rate | deny rate |
|---|---|---|---|---|
| 0.100% | 0.0000 | n/a | 0.6320 | 0.3680 |
| 0.500% | 0.0000 | n/a | 0.6320 | 0.3680 |
| 1.000% | 0.0000 | n/a | 0.6320 | 0.3680 |
| 2.000% | 0.0000 | n/a | 0.6320 | 0.3680 |
| 5.000% | 0.0000 | n/a | 0.6320 | 0.3680 |
