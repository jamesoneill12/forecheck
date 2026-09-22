# Independent LLM-judge labels

Every label in the synthetic dataset is derived deterministically from the generator's
own `LatentScenario` (`forecheck.data.labeling`). That is exact and reproducible, but it
is also self-referential: a reviewer can reasonably ask "how do you know the *labels*
are right, not just internally consistent with the thing that produced them?" This
workflow answers that by having a frontier LLM judge a stratified sample of examples
blind — it never sees the latent scenario or the generator's label — and reports how
often the judge and the generator agree.

Implementation: `src/forecheck/judge/`. CLI: `forecheck judge sample|label|agreement`,
plus `forecheck evaluate --labels-from` to re-score any backend against judge labels.

## 1. What this does and does not establish

**Blindness.** The judge is given exactly the rendered context a downstream classifier
sees (`forecheck.inference.serialization.render_context`, optionally identity-stripped)
and the same eleven `RiskDimension` definitions the classifier's labels are keyed to
(`src/forecheck/judge/dimensions.py`). It is never given the `LatentScenario`, the
generator's own `LabelSet`, or any hint about which generator produced the row.

**What agreement establishes.** High judge/generator agreement on a dimension means the
fact that dimension names is *observable in the rendered text* — a competent, blind
reader can recover it. That is necessary for the dimension to be learnable by any
text-only classifier, forecheck's included, and it is independent evidence that the
generator's label derivation matches what the text actually says.

**What agreement does not establish.** It is not a ground-truth check. The judge is
itself an LLM classifying natural-language context, and it shares failure modes with
LLM-based classifiers in general: it can be fooled by the same prompt-injection framing,
miss the same subtle scope violations, and default to the same base rates a model
trained on similar data would. Perfect judge/generator agreement is consistent with
"the label is correct" and also with "the label is exactly as recoverable from the text
as the generator intended, and the judge and the generator both use the same textual
cues" — it cannot distinguish those. Treat agreement as evidence of label
*observability*, never as a substitute for human or real-world (class-3, per
`docs/evaluation-plan.md` §1) evaluation.

Low agreement on a dimension is more informative than high agreement: it means either
the rendered context under-specifies the dimension (a data-generation gap) or the
dimension's definition is ambiguous enough that two competent readers disagree (a
taxonomy gap) — both are actionable findings `disagreements.jsonl` is built to surface.

## 2. Sampling (`forecheck judge sample`)

```
forecheck judge sample --data <dataset-dir> --splits heldout_family,heldout_policy_kind \
  --n 600 --seed 20260922 --out judge_sample.jsonl
```

Draws a stratified, greedy coverage-maximising sample (`src/forecheck/judge/sampling.py`):
every `(dimension, label in {yes, no})` cell is filled to `--cell-target` (default 20)
rows where that many are available in the pool, and — subject to that — tool families
and policy-predicate kinds are spread as evenly as possible. `NOT_APPLICABLE` cells are
never targeted directly (they carry no yes/no signal to compare against) but do appear
in sampled rows' `generator_labels` and are compared in the agreement step.

Prints a coverage table and writes `coverage.json` next to `--out`, so a reviewer can
see which cells the pool could not fill (e.g. a rare dimension with fewer than 20
positives total) before spending judge budget.

Each output row (`JudgeSampleRow`) carries the example id, both the full and
identity-stripped renderings, the tool family, the policy-predicate kinds present, and
the generator's own label for every dimension — the last field only read by
`judge agreement`, never shown to the judge itself.

## 3. Labelling (`forecheck judge label`)

```
export OPENAI_API_KEY=...          # openai_compat
forecheck judge label --sample judge_sample.jsonl --provider openai_compat \
  --model gpt-4o-mini --out judge_labels.jsonl --concurrency 8
```

One chat call per example: a system prompt with the eleven dimension definitions and
the required JSON output schema, a user message that is exactly the rendered context
(add `--strip-identity` to judge the identity-stripped rendering instead). The judge
must return `yes|no|not_applicable` plus a <=20-word rationale for every dimension, as a
single JSON object. Parsing is strict (`src/forecheck/judge/labeling.py`): a completion
that fails to parse, or is missing a dimension, or uses an invalid value, is retried
once; if the retry also fails, that example's unparsed dimensions are recorded as
unparseable (`parse_ok=False`), never guessed at.

`--out` doubles as an idempotency cache keyed by `(model, example_id, strip_identity)`:
re-running the same command only calls the provider for rows not already in `--out`,
so an interrupted or partially-budgeted run can be resumed by rerunning the same
command. `--max-examples N` caps a run to the first N sample rows, for a cheap smoke
test before spending the full budget.

Credentials come only from environment variables — `OPENAI_API_KEY` and optional
`OPENAI_BASE_URL` for `--provider openai_compat`, `ANTHROPIC_API_KEY` for
`--provider anthropic` — never a CLI flag or a config file, and never logged.

### `--provider codex_cli` (no API key)

```
forecheck judge label --sample judge_sample.jsonl --provider codex_cli \
  --model gpt-5.6-sol --reasoning-effort low --out judge_labels.jsonl
```

Shells out to a locally installed, already-logged-in Codex CLI instead of calling an
HTTP API, so it needs no `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` — it bills against the
operator's own ChatGPT plan. The binary is resolved with `shutil.which("codex")`,
overridable via `FORECHECK_CODEX_BIN`. Each call runs `codex exec` in an isolated
scratch directory (`--cd`, `--ephemeral`, `--skip-git-repo-check`, `-s read-only`) so
codex never reads repository files, and the judge's completion is read from
`--output-last-message` rather than parsed off stdout. `--reasoning-effort` (default
`low`) maps to `-c model_reasoning_effort=...`; default concurrency is 6, lower than
the other providers' 8, since each call is a local subprocess rather than an async HTTP
request. `estimate_cost_usd` always returns `None` for this provider — there is no
per-token price to report — and the CLI prints a note instead of a dollar figure.

Because it depends on an interactive, per-machine `codex` login, `codex_cli` is a local
convenience for a spot-check or a budget-free smoke test, not something CI can run.

**Cost estimate.** Printed at the end from the API response's own token counts:
`cost = input_tokens / 1e6 * price_in + output_tokens / 1e6 * price_out`, using a small
built-in list-price table (`src/forecheck/judge/providers.py`); an unlisted model still
prints exact token totals with a note that the dollar cost is unknown. Cached rows from
a previous run are excluded from the printed totals since no call was made for them.

## 4. Agreement (`forecheck judge agreement`)

```
forecheck judge agreement --sample judge_sample.jsonl --labels judge_labels.jsonl \
  --out reports/judge-agreement/
```

Per dimension (`src/forecheck/judge/agreement.py`): Cohen's kappa and raw agreement %
over the rows where both the generator and the judge produced an evaluable
`yes/no/not_applicable` value, a 4x4 confusion table (generator row vs judge column,
`not_applicable` as its own category rather than a negative, plus an `unparseable`
column for rows the judge never parsed), written as `agreement.json` and `agreement.md`.
Every per-dimension mismatch is written to `disagreements.jsonl` (example id, dimension,
generator label, judge label, judge's rationale) for manual review.

## 5. Re-scoring against judge labels (`forecheck evaluate --labels-from`)

```
forecheck evaluate --run <run-dir> --split heldout_family --class synthetic_in_distribution \
  --labels-from judge_labels.jsonl
```

Restricts the evaluated split to the example ids present in `--labels-from` and
replaces each one's `LabelSet` with the judge's verdicts (a dimension the judge never
parsed becomes `LabelValue.UNDETERMINED`, excluded from metrics exactly like an
abstained prediction). Every other flag and the report path are unchanged — this is a
drop-in relabelling of the same `forecheck.evaluation.runner.evaluate` path, not a
separate report format. The header records `Labels: llm judge <model>` so a reader
never mistakes a judge-scored report for one scored against generator ground truth.

## 6. End-to-end

```
export OPENAI_API_KEY=...
forecheck judge sample --data data/synthetic-v5 --splits heldout_family,heldout_policy_kind \
  --n 600 --seed 20260922 --out judge/sample.jsonl
forecheck judge label --sample judge/sample.jsonl --provider openai_compat \
  --model gpt-4o-mini --out judge/labels.jsonl --concurrency 8
forecheck judge agreement --sample judge/sample.jsonl --labels judge/labels.jsonl \
  --out judge/agreement/
forecheck evaluate --run <run-dir> --split heldout_family --class synthetic_in_distribution \
  --labels-from judge/labels.jsonl
```
