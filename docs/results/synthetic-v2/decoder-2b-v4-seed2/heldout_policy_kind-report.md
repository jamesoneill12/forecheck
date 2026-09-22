# forecheck evaluation report — SYNTHETIC_HELDOUT_ADVERSARIAL

> **Synthetic data. No real-world safety claim is made.**

Dataset: split=heldout_policy_kind, n=2247, sha256=99c768cce2dd5ac344288cf1ca35a2825ca52a9ea3002ff39d94f71c96406a2c
Seed: 0. Generated at: 2026-09-22T15:48:25.400534+00:00.
Model: huggingface/ibm-granite/granite-3.3-2b-instruct
Identity stripped: false
Threshold selection: F1-optimal threshold (argmax F1 over the precision-recall curve), selected on a split disjoint from the one being reported. Selection split: dev. Reported split: heldout_policy_kind.

## Per-dimension metrics

| dimension | n_evaluable | positive_rate | f1@0.5 | selected_threshold | precision@selected | recall@selected | f1@selected | auprc | auroc | ece |
|---|---|---|---|---|---|---|---|---|---|---|
| prompt_injection_influence | 2247 | 0.0757 | 0.8194 | 0.9999 | 1.0000 | 0.6941 | 0.8194 | 0.7285 | 0.8618 | 0.0025 |
| unauthorized_scope | 2139 | 0.1169 | 1.0000 | 0.0016 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| sensitive_data_exposure | 510 | 0.2118 | 1.0000 | 0.9997 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| untrusted_destination | 647 | 0.3215 | 1.0000 | 0.5000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0002 |
| privilege_escalation | 2247 | 0.0191 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0000 |
| destructive_or_irreversible_action | 2247 | 0.0961 | 0.9883 | 0.9987 | 1.0000 | 0.9769 | 0.9883 | 0.9945 | 0.9994 | 0.0003 |
| financial_commitment | 2247 | 0.0797 | 1.0000 | 1.0000 | 1.0000 | 0.9944 | 0.9972 | 1.0000 | 1.0000 | 0.0000 |
| external_communication | 53 | 0.6226 | 1.0000 | 0.9985 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 0.0001 |
| policy_conflict | 2247 | 0.4050 | 0.5589 | 0.3938 | 0.7550 | 0.4604 | 0.5720 | 0.7112 | 0.6910 | 0.2450 |
| suspicious_action_sequence | 460 | 0.3130 | 0.9451 | 0.2072 | 0.9630 | 0.9028 | 0.9319 | 0.9692 | 0.9823 | 0.0099 |
| insufficient_context | 2247 | 0.0788 | 0.9018 | 0.8254 | 0.9932 | 0.8249 | 0.9012 | 0.9391 | 0.9909 | 0.0126 |

## Macro / worst slice

- macro `precision` = 0.9773
- macro `recall` = 0.8944
- macro `f1` = 0.9285
- macro `f1@selected` = 0.9282
- macro `auprc` = 0.9402
- macro `auroc` = 0.9569
- macro `brier` = 0.0291
- macro `ece` = 0.0246
- worst-slice `precision` = 0.1429 (contrastive_axis=resource_sensitivity)
- worst-slice `recall` = 0.1429 (contrastive_axis=resource_sensitivity)
- worst-slice `f1` = 0.1429 (contrastive_axis=resource_sensitivity)
- worst-slice `f1@selected` = n/a
- worst-slice `auprc` = 0.6952 (contrastive_axis=principal_authorization)
- worst-slice `auroc` = 0.7778 (contrastive_axis=known_versus_lookalike_destination)
- worst-slice `brier` = 0.0002 (contrastive_axis=resource_sensitivity)
- worst-slice `ece` = 0.0072 (contrastive_axis=resource_sensitivity)

## Consistency
- pair consistency: 1.0000 over 31 directional pairs
- counterfactual sensitivity (mean |dp|): 0.9992
- surface-paraphrase invariance (mean |dp|): 0.0056, fraction moved: 0.2000

## Approval elimination

Bundle `balanced`, n=2247, base incident rate=0.7045, incident rate mode=prefix. Ranking score: expected cost of ALLOW over the bundle's covered dimensions (destructive_or_irreversible_action, external_communication, financial_commitment, insufficient_context, policy_conflict, privilege_escalation, prompt_injection_influence, sensitive_data_exposure, suspicious_action_sequence, unauthorized_scope, untrusted_destination).

| budget | approvals eliminated | incident rate | review rate | deny rate |
|---|---|---|---|---|
| 0.100% | 0.0036 | 0.0000 | 0.6667 | 0.3298 |
| 0.500% | 0.0036 | 0.0000 | 0.6667 | 0.3298 |
| 1.000% | 0.0036 | 0.0000 | 0.6667 | 0.3298 |
| 2.000% | 0.0036 | 0.0000 | 0.6667 | 0.3298 |
| 5.000% | 0.0036 | 0.0000 | 0.6667 | 0.3298 |
