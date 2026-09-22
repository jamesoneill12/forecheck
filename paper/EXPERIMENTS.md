# Experiment matrix for the paper

One line per experiment the paper still needs, the recipe/config that
produces it, and status. Numbers currently in the paper are sourced from
`docs/results/synthetic-v2/README.md` and the linked evaluation docs; every
row below either fills a `\todo{pending: ...}` in `paper/` or backs a claim
that is currently under-supported.

| Experiment | Recipe / config | Status |
|---|---|---|
| 3 training seeds for decoder v4 (seed variance) | `configs/eks/train-2b-b200-v4-recipe.yaml` with `--seed 0/1/2` | seeds 0 and 1 done: macro AUPRC stable to ~0.005, `heldout_policy_kind` `policy_conflict` 0.752 (seed 0) vs 0.689 (seed 1); seed 2 running (`2b-v4-seed2`) |
| 8B size control (decoder, v4 data) | `configs/training/8b.yaml` + `configs/eks/train-2b-b200-v4-recipe.yaml` data dir (LoRA on `granite-3.3-8b-instruct`) | done: macro 0.956/0.958/0.951/0.964 (test/heldout_family/heldout_policy_kind/heldout_policy_phrasing); `heldout_policy_kind` `policy_conflict` 0.851, vs 2B's 0.752 |
| v5: 30 policy kinds, 4 withheld, decoder 2B | `configs/eks/train-2b-b200-v5-recipe.yaml` (ADR 0011) | done: macro 0.957/0.951/0.941/0.970; `heldout_policy_kind` `policy_conflict` 0.704 -- within seed noise of v4, does not fix kind generalisation; seed 1 running (`2b-v5-seed1`); seed 2 recipe written, not yet submitted |
| Agent self-judgment, decoder-comparable split coverage (test + adversarial for both 2B/8B, full identity + stripped) | `configs/eks/eval-agent-self-b200-recipe.yaml` | done for heldout_family (2B, 8B) and adversarial (8B); 8B-v4 checker row-for-row comparison done (`eval-v4-idself`, macro delta 0.45--0.90 AUPRC per dimension, `agent-self-8b-v4/heldout_family-report.md`); test split and 2B/adversarial not yet run |
| Encoder granite-embedding-r2 on v4, identity-stripped | same training run as `encoder-granite-embedding-r2-v4`, eval with `--strip-identity` | todo (v2/v3 stripped exists; v4 stripped not run) |
| Decoder 2B v4, identity-stripped (fills Table 1's `---` cell) | `configs/eks/train-2b-b200-v4-recipe.yaml` eval with `--strip-identity` | done: 0.790 heldout_family / 0.787 test (`decoder-2b-v4/heldout_family-noid-report.md`, `test-noid-report.md`) |
| Decoder 8B v4, identity-stripped (fills Table 1's 8B `---` cell) | `configs/training/8b.yaml` eval with `--strip-identity` | running (`eval-8b-v4-noid`) |
| Approval-elimination curve, decoder v4, reweighted to 5% base rate | `forecheck evaluate --run <v4-run-dir> --approval-curve balanced --approval-target-base-rate 0.05 --approval-incident-rate-mode smoothed` | done: 0.903/0.952/0.992 eliminated at 1%/2%/5% budget, matching v2 within a point |
| Real-data probe: 200 hand-labelled Fin-shaped tool calls through v4 model | no recipe yet -- needs a small hand-labelling pass + `forecheck evaluate --backend hf --run <v4-run-dir> --class 3` once a class-3 split exists | todo (LLM-judge labels) |
| Ablation: train without identity fields (model trained on stripped input, not just evaluated on it) | proposed new recipe `configs/eks/train-2b-b200-v4-identity-stripped-recipe.yaml` (v4 data regenerated/rendered with `--strip-identity` applied at *training* time, not just eval time) | running (`2b-v4-noid`) -- distinguishes "the model never learned to use identity" from "the model learned to use it but the signal is fragile at eval time"; currently only eval-time stripping exists for any arm |

## Notes

- Every "todo" row above corresponds to a `\todo{pending: ...}` macro in the
  paper (`paper/sections/*.tex`, `paper/appendix.tex`) except the real-data
  probe and the train-time identity-stripped ablation, which are named in
  `sections/limitations.tex` and `sections/conclusion.tex` prose rather than
  a table cell.
- The train-time identity-stripped ablation is new relative to
  `docs/research-direction.md`'s run order; it closes the gap between
  "stripping at eval time breaks three dimensions" (shown) and "the model
  never had a mechanism to use identity at all" (assumed, not directly
  tested) by training a second decoder on data rendered without identity
  fields from the start and comparing its ceiling on those three dimensions
  against the full model's eval-time-stripped ceiling.
