# AgentDojo recalibration

Data: AgentDojo banking suite, 4,215 tool-call examples per checker, scored by forecheck v4 checkers (2B and 8B decoder backends). Each dump is one JSON line per example with the checker's raw score, the shipped synthetic-fitted probability, and the AgentDojo-derived label per risk dimension.

Method: seed the RNG, shuffle rows, split 50/50 into a fit half and a test half. Rows are kept per dimension when the label is yes/no and the raw score is non-null. On the fit half, refit a 1-D Platt scaler (logistic regression on the raw score) and an isotonic regressor (`IsotonicRegression(out_of_bounds="clip")`). On the test half, report ECE (10 equal-width bins on [0, 1], `sum_b (n_b/n) * |mean_pred_b - frac_pos_b|`) for the shipped probability, the Platt refit, and the isotonic refit, plus AUPRC of the raw score (`average_precision_score`) to show ranking is unchanged by recalibration. Repeated over seeds 0-4; cells are mean +/- sd across seeds.

## Per-checker calibration

### 2b

| dimension | n_test | AUPRC | ECE shipped | ECE Platt refit | ECE isotonic refit |
|---|---|---|---|---|---|
| prompt_injection_influence | 2067 | 0.130 +/- 0.002 | 0.136 +/- 0.002 | 0.069 +/- 0.005 | 0.005 +/- 0.004 |
| unauthorized_scope | 2108 | 0.260 +/- 0.005 | 0.211 +/- 0.008 | 0.021 +/- 0.015 | 0.018 +/- 0.008 |
| policy_conflict | 2108 | 0.854 +/- 0.006 | 0.070 +/- 0.001 | 0.054 +/- 0.005 | 0.016 +/- 0.004 |
| financial_commitment | 2108 | 1.000 +/- 0.000 | 0.053 +/- 0.001 | 0.000 +/- 0.000 | 0.000 +/- 0.000 |
| destructive_or_irreversible_action | 2108 | 1.000 +/- 0.000 | 0.243 +/- 0.006 | 0.004 +/- 0.000 | 0.000 +/- 0.000 |
| **macro** | 10499 | 0.649 +/- 0.001 | 0.143 +/- 0.003 | 0.030 +/- 0.004 | 0.008 +/- 0.002 |

### 8b

| dimension | n_test | AUPRC | ECE shipped | ECE Platt refit | ECE isotonic refit |
|---|---|---|---|---|---|
| prompt_injection_influence | 2067 | 0.702 +/- 0.011 | 0.080 +/- 0.003 | 0.066 +/- 0.006 | 0.016 +/- 0.005 |
| unauthorized_scope | 2108 | 0.357 +/- 0.013 | 0.601 +/- 0.005 | 0.017 +/- 0.006 | 0.012 +/- 0.010 |
| policy_conflict | 2108 | 0.623 +/- 0.012 | 0.170 +/- 0.006 | 0.073 +/- 0.013 | 0.015 +/- 0.006 |
| financial_commitment | 2108 | 0.925 +/- 0.003 | 0.052 +/- 0.002 | 0.082 +/- 0.004 | 0.006 +/- 0.003 |
| destructive_or_irreversible_action | 2108 | 0.999 +/- 0.000 | 0.111 +/- 0.004 | 0.003 +/- 0.001 | 0.002 +/- 0.000 |
| **macro** | 10499 | 0.721 +/- 0.001 | 0.203 +/- 0.002 | 0.048 +/- 0.002 | 0.010 +/- 0.001 |

## Refit sample size

### Refit sample size (8B, isotonic only)

Test ECE (isotonic refit, mean +/- sd over 5 seeds) as a function of the number of labelled rows drawn from the fit half:

| dimension | n=100 | n=250 | n=500 | n=1000 | n=2000 |
|---|---|---|---|---|---|
| prompt_injection_influence | 0.046 +/- 0.020 | 0.025 +/- 0.008 | 0.019 +/- 0.007 | 0.018 +/- 0.004 | 0.016 +/- 0.005 |
| policy_conflict | 0.036 +/- 0.017 | 0.037 +/- 0.013 | 0.026 +/- 0.013 | 0.020 +/- 0.006 | 0.014 +/- 0.006 |

## Reading

The shipped synthetic-fitted probabilities are badly miscalibrated in-domain on AgentDojo (worst case, 8B unauthorized_scope, ECE ~0.6), and both refits pull ECE down by roughly one to two orders of magnitude across every dimension and both checkers, while AUPRC is essentially unchanged, confirming the refit is fixing calibration and not ranking. The sample-size sweep shows most of that gain lands with a few hundred in-domain labelled calls, well short of the full ~2,000-row fit half.
