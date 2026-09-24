# Compiled-predicate symbolic baseline (current generator: 30 policy kinds, 4 withheld)

`RuleBaselineBackend` is deliberately uninformative on `unauthorized_scope` (never
intersects entitlements with delegated scope) and `policy_conflict` (constant `0.5`
whenever a policy is supplied), so the paper had no non-trivial comparator on exactly
the dimensions it is about. `SymbolicBaselineBackend`
(`src/forecheck/evaluation/symbolic_baseline.py`) closes that gap using only facts the
typed `ActionContext` exposes, plus the public tool catalogue, and delegates every other
dimension unchanged to `RuleBaselineBackend`. Selectable as `--backend symbolic_baseline`
everywhere `--backend rule_baseline` is (`forecheck evaluate`, `forecheck calibrate`).

## What the typed context does and does not expose

**`unauthorized_scope`.** `ActionContext` carries `principal.entitlements` and
`agent.delegated_scopes` directly, but not a proposed action's *required* scopes. Those
come from `forecheck.data.tools.get_tool(tool_name).required_scopes` — a lookup against
the tool catalogue, the same kind of typed metadata a real policy engine would hold for
a registered tool, never from rendered text. The predicate is then a direct set
intersection: `required - (entitlements ∩ delegated_scopes)`. Unknown tool names (not in
the catalogue) abstain at `0.5`.

**`privilege_escalation`.** The rendered context has no first-class "authority before /
after" field. The generator only attaches `authority_before` / `authority_after` into
`proposed_action.arguments` for tools that can change authority
(`ToolSpec.changes_authority`); see `forecheck/data/rendering.py::_build_arguments`. When
those keys are present the backend reproduces the generator's own label rule exactly
(`forecheck.data.labeling._privilege_escalation`) using the typed arguments plus the
catalogue's `operation` and `changes_authority`. When absent, `0.05` is the *correct*
answer, not a guess: a tool that cannot change authority and isn't a `GRANT` cannot
escalate by construction. There is no typed signal at all for the *effective* authority a
principal already holds beyond `entitlements ∩ delegated_scopes` used for the `GRANT`
branch.

**`policy_conflict`.** `PolicyStatement.text` is free text; there is no typed predicate
field on `ActionContext`. The backend inverts the generator's own phrasing templates
(`forecheck/data/rendering.py::_POLICY_CLAUSE_TEMPLATES` and
`_POLICY_WRAPPER_TEMPLATES`) into regexes with named capture groups, matches each
supplied clause, and evaluates the recovered predicate kind against typed context: tool
catalogue lookups, `resources[].sensitivity/operation/record_count_estimate`,
`environment.stage/change_freeze/region/labels[local_hour|is_weekend]`,
`destination.relationship/verified`, `financial.amount/currency`, and the same
`proposed_action.arguments` keys used for privilege escalation (`manager_approved`,
`customer_consent_given`, `encryption_in_transit`, `reason`, `records_processed_today`,
`cross_tenant_resource`, `pii_fields`, `channel`, `export_format`, `ticket_reference`).
Two of the 30 policy-predicate kinds are structurally unanswerable from typed fields —
`require_dry_run_first` and `forbid_action_after_failed_auth_in_trajectory` both depend
on facts (`dry_run_performed`, `failed_auth_in_trajectory`) that only ever reach the
context as free trajectory `result_summary` text, never a typed field — so a clause of
either kind always abstains even when its text is recognized. The compiler's known-kind
set also **excludes** the 4 kinds withheld by
`forecheck.data.splitting.default_heldout_policy_kinds()`, the same kinds a trained model
never sees, so it abstains on the `heldout_policy_kind` split by construction rather than
by accident. It does *not* exclude the withheld paraphrase index (`3`): all four
paraphrases per known kind are compiled, so the backend is robust to
`heldout_policy_phrasing` almost by design — a point of genuine contrast with a learned
model, which has to generalize to that wording rather than already knowing it.

A clause that matches no known template, or matches a kind whose predicate needs an
unavailable typed fact, contributes an **abstain** (`0.5`) for that clause. The
dimension-level score is `0.95` if any clause is both parsed and violated, `0.05` if
every clause was parsed and none were violated, else `0.5`.

## Data: regenerating v4 splits

The rule-baseline reference numbers in the paper trace to
`docs/results/synthetic-v2/decoder-2b-v4/rule_baseline/*.md`, produced from
`configs/data/train_medium.yaml` (seed `424242`, offline renderer). That config still
generates on today's `main` in **33s** for `data generate` and **10s** for `data split`
(49,996 raw rows on a 14-core laptop CPU) — comfortably under the 20-minute budget — so
all three requested splits were regenerated in full, not subsampled:

```
uv run forecheck data generate --offline --config configs/data/train_medium.yaml --out /tmp/forecheck_v4_repro
uv run forecheck data split /tmp/forecheck_v4_repro
```

Resulting split sizes: `heldout_family`=6692, `heldout_policy_kind`=2321,
`heldout_policy_phrasing`=3270, `test`=4348 (`train`=22470, `calibration`=4519,
`dev`=4393, `adversarial`=1983).

## Sanity check against the paper's rule-baseline numbers — discrepancy, not a match

| dimension | split | paper (rule_baseline) | reproduced (rule_baseline) |
|---|---|---|---|
| unauthorized_scope | heldout_family | 0.507 | 0.4838 |
| privilege_escalation | heldout_family | 0.364 | 0.3218 |
| policy_conflict | heldout_family | 0.370 | 0.2999 |
| policy_conflict | heldout_policy_kind | 0.405 | 0.3253 |

Same ballpark and same ranking, but not an exact reproduction. Root cause, found by
reading `PolicyPredicateKind`'s own docstring rather than by tuning anything: **ADR 0011
added 15 new policy-predicate kinds after v4 was generated** ("the first 15 members
predate ADR 0011 ... the 15 members from `REQUIRE_MANAGER_APPROVAL_ABOVE_AMOUNT` on were
added by ADR 0011"), and also raised `DEFAULT_HELDOUT_POLICY_KIND_COUNT` from 2 to 4.
Regenerating on today's `main` therefore samples policy predicates from 30 kinds instead
of v4's 15, and withholds 4 kinds instead of 2, which shifts both the `policy_conflict`
positive rate and the `heldout_policy_kind` split's membership. This is a version
mismatch in the generator between v4 and `main`, not a bug in either baseline. No
parameter was tuned to try to close this gap.

## Results: AUPRC per dimension, n, positive rate

Commands (repeated per split, `--class synthetic_heldout_adversarial` for the three
heldout splits and `synthetic_in_distribution` for `test`; `--threshold-split none`
since only AUPRC is reported here):

```
uv run forecheck evaluate --run /tmp/forecheck_v4_repro/run --data /tmp/forecheck_v4_repro \
  --split <split> --class <class> --backend rule_baseline \
  --threshold-split none --out /tmp/forecheck_v4_repro/reports/rule_baseline/<split>

uv run forecheck evaluate --run /tmp/forecheck_v4_repro/run --data /tmp/forecheck_v4_repro \
  --split <split> --class <class> --backend symbolic_baseline \
  --threshold-split none --out /tmp/forecheck_v4_repro/reports/symbolic_baseline/<split>
```

### heldout_family (n=6692)

| dimension | n_evaluable | positive_rate | rule_baseline AUPRC | symbolic_baseline AUPRC |
|---|---|---|---|---|
| unauthorized_scope | 6393 | 0.1215 | 0.4838 | **1.0000** |
| privilege_escalation | 6692 | 0.0693 | 0.3218 | **0.9831** |
| policy_conflict | 1894 | 0.3025 | 0.2999 | **0.9004** |

### heldout_policy_kind (n=2321)

| dimension | n_evaluable | positive_rate | rule_baseline AUPRC | symbolic_baseline AUPRC |
|---|---|---|---|---|
| unauthorized_scope | 2228 | 0.1095 | 0.4960 | **1.0000** |
| privilege_escalation | 2321 | 0.0164 | 0.3088 | **0.9744** |
| policy_conflict | 2316 | 0.3303 | 0.3253 | **0.6000** |

### heldout_policy_phrasing (n=3270)

| dimension | n_evaluable | positive_rate | rule_baseline AUPRC | symbolic_baseline AUPRC |
|---|---|---|---|---|
| unauthorized_scope | 3113 | 0.1211 | 0.4826 | **1.0000** |
| privilege_escalation | 3270 | 0.0156 | 0.2989 | **0.9444** |
| policy_conflict | 3259 | 0.3335 | 0.3331 | **0.9560** |

### test (n=4348, for reference)

| dimension | n_evaluable | positive_rate | rule_baseline AUPRC | symbolic_baseline AUPRC |
|---|---|---|---|---|
| unauthorized_scope | 4146 | 0.1252 | 0.5118 | **1.0000** |
| privilege_escalation | 4348 | 0.0179 | 0.3317 | **0.9630** |
| policy_conflict | 749 | 0.3031 | 0.3047 | **0.9466** |

`unauthorized_scope` and `privilege_escalation` are near-exact reproductions of the
generator's own label formula from typed fields, so AUPRC is at or near ceiling on every
split, including `heldout_policy_kind`/`heldout_policy_phrasing` (neither dimension is
policy-kind-gated). `policy_conflict` is markedly weaker specifically on
`heldout_policy_kind` (0.600 vs 0.90-0.96 elsewhere) — exactly the split engineered to
contain withheld-kind clauses the compiler cannot know by construction.

## Policy-clause abstain rate per split

Computed directly from `SymbolicBaselineBackend.policy_clause_stats` after scoring
`policy_conflict` over each split's full context set:

```
uv run python -c "
from pathlib import Path
from forecheck.data.io import read_jsonl
from forecheck.contracts import RiskDimension
from forecheck.evaluation.symbolic_baseline import SymbolicBaselineBackend

for split in ['test', 'heldout_family', 'heldout_policy_kind', 'heldout_policy_phrasing']:
    examples = read_jsonl(Path(f'/tmp/forecheck_v4_repro/{split}.jsonl'))
    backend = SymbolicBaselineBackend()
    backend.score_batch([e.context for e in examples], [RiskDimension.POLICY_CONFLICT])
    s = backend.policy_clause_stats
    print(split, s.total, s.unmatched, s.undecidable, s.decided, s.abstain_rate)
"
```

| split | clauses | unmatched (unknown template) | undecidable (matched, no typed fact) | decided | abstain rate |
|---|---|---|---|---|---|
| test | 995 | 0 | 104 | 891 | 10.45% |
| heldout_family | 2789 | 380 | 258 | 2151 | 22.88% |
| heldout_policy_kind | 3718 | 2365 | 139 | 1214 | 67.35% |
| heldout_policy_phrasing | 5146 | 0 | 512 | 4634 | 9.95% |

`heldout_policy_kind` abstains overwhelmingly via **unmatched** clauses (withheld-kind
phrasing the compiler has never seen), as designed. `heldout_policy_phrasing` has zero
unmatched clauses — every paraphrase of every known kind is compiled, so unseen wording
of a *known* kind is not a source of abstention here, unlike for a trained model. The
remaining ~10% abstain rate on `test`/`heldout_policy_phrasing` is the structural floor
from `require_dry_run_first` and `forbid_action_after_failed_auth_in_trajectory`, which
no typed field can ever resolve.

## Tests

`tests/evaluation/test_symbolic_baseline.py`, 14 tests, all passing:

```
uv run pytest tests/evaluation/test_symbolic_baseline.py -q
```

Covers: delegation of every non-target dimension to `RuleBaselineBackend`;
`unauthorized_scope` low/high on covered/missing entitlement or delegated scope, and
abstain on an unknown tool; `privilege_escalation` high when authority widens, low when
unchanged, low for a tool that never touches authority; `policy_conflict` low with no
policies, high/low on a real `max_financial_amount` clause at different amounts, abstain
on unrecognized clause text, and abstain on a clause instantiating a withheld policy
kind's own template. Full repo suite (`uv run pytest tests/ -q`): 881 passed, 4 skipped,
0 failed — no regressions from wiring `symbolic_baseline` into `resolve_backend`.
