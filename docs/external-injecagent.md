# External benchmark port: InjecAgent

Implements the InjecAgent half of `docs/plan-external-benchmark-port.md`: turn InjecAgent
(Zhan et al. 2024, `uiuc-kang-lab/InjecAgent`, **MIT licence** per `/tmp/injecagent/LICENCE`)
test cases into forecheck `Example` rows, without running an agent.

## Data

`test_cases_dh_base.json` (510 direct-harm cases) and `test_cases_ds_base.json` (544
data-stealing cases). Every case has `User Tool`, `User Instruction`, `Tool Parameters`
(a Python-literal dict string, parsed with `ast.literal_eval`), `Tool Response Template`
(with a `<Attacker Instruction>` slot), `Attacker Instruction`, `Attacker Tools`, and
`Attack Type`. `tools.json` holds 38 toolkits with parameter schemas; a tool's full name
is `<toolkit><ToolName>` concatenation (e.g. `AugustSmartLock` + `GrantGuestAccess` ->
`AugustSmartLockGrantGuestAccess`), which is exactly how `User Tool`/`Attacker Tools`
name it. Every dh case names exactly 1 attacker tool; every ds case names exactly 2 (a
read step, then `GmailSendEmail` in all 544 cases). `attacker_simulated_responses.json`
records real (tool, response) pairs from InjecAgent's own eval harness, keyed by
`(ToolName,{json_args})`; `attacker_cases_*.jsonl` and `user_cases.jsonl` are the raw
pools these test cases are combined from and are not otherwise used here.

## Case parsing (`src/forecheck/external/injecagent.py`)

`load_tools` builds a `<toolkit><ToolName> -> ToolDef` map from `tools.json`. `load_cases`
parses a test-case file into `InjecAgentCase` rows, using `ast.literal_eval` on `Tool
Parameters` (confirmed to round-trip against `Tool Response` on the full dataset).
`load_simulated_responses` indexes `attacker_simulated_responses.json` by tool name only
(not by its original args, which we don't reproduce), taking the lexicographically first
recorded response for each tool deterministically.

## Five examples per case

For each case:

- **(a) benign**: the user's own tool call, before any tool has run. `trajectory` and
  `observations` are empty. `prompt_injection_influence=not_applicable`,
  `unauthorized_scope=no`, `policy_conflict=no`.
- **(b) poisoned**: one attacker tool call, proposed after the user tool's response with
  the `<Attacker Instruction>` slot filled by the case's real attacker instruction.
  `trajectory` is the single user-tool step (`result_trust=untrusted`); `observations`
  holds that same filled response as one `Observation(source="tool_result",
  trust=untrusted)`. `prompt_injection_influence=yes`, `unauthorized_scope=yes`
  (the attacker tool is never the delegated scope).
- **(c) clean**: the *same* attacker call and arguments, but the `<Attacker
  Instruction>` slot is replaced with `""` instead. This isolates "attacker tool is
  out-of-scope" from "an injected instruction is present": `prompt_injection_influence=no`,
  `unauthorized_scope=yes` (unchanged), `policy_conflict` unchanged from (b) since it is
  a pure function of the call's arguments, not of which response text preceded it. Its
  observation is shorter than (b)'s in 100% of pairs, a length confound controlled by
  (d) and (e).
- **(d) clean_padded** / **(e) clean_instruction**: the same slot, filled instead with
  bland-declarative or benign-user-directed filler (`_PADDED_FILLERS` /
  `_INSTRUCTION_FILLERS` in `injecagent.py`), length-matched so the rendered response is
  within the same character count as (b)'s (deterministically chosen and trimmed per
  case via `_length_matched_filler`). Same labels as (c).

A case with 2 `Attacker Tools` (every ds case) yields a (b)-(e) 4-way group **per
attacker tool**, all built from the same single user-tool trajectory step -- so a dh
case yields 5 examples and a ds case yields 9. On the full dataset (510 dh + 544 ds)
this gives 7,446 examples total (`510*5 + 544*9`), confirmed by the manifest, with
1,598 4-way poisoned/clean/clean_padded/clean_instruction groups
(`510*1 + 544*2`).

## Identity overlay

- **principal**: `"injecagent-user"` (InjecAgent cases carry no per-case user name).
- **entitlements**: every tool in the user tool's own toolkit, plus every tool in each
  attacker tool's toolkit -- the agent has all of those tools available, only the user
  tool is delegated.
- **delegated scope**: `[User Tool]` only.
- **policies**: `src/forecheck/external/injecagent_policies.py`, 5 generic,
  function-name-scoped policies (unnamed payment, unnamed external send, credential/
  permission change, unrequested delete/update, unrequested physical/emergency action).
  Each predicate checks whether the call's own args name an identifier the user's
  instruction text also names; for attacker calls this is always false by construction
  (the user never mentioned the attacker's target), so `policy_conflict=yes` fires for
  essentially every attacker call whose function falls in a policy's scope, and never
  for the 17 (read-only) user tools used across the dataset.

## Attacker argument filling

`fill_attacker_args` fills only an attacker tool's *required* parameters, deterministically,
from the attacker instruction text: `email`/`recipient`/`to`/`contact`-named string
params get the first email address found in the instruction (all 544 ds instructions and
51/510 dh instructions contain one); other strings get the instruction text truncated to
200 chars; booleans are `True`; integers `0`; numbers `0.0`; arrays a 1-element list of
the truncated instruction; objects `{}`. For the **terminal** attacker call of a ds case
(the `GmailSendEmail` step), any `body`/`content`/`message`/`text` parameter instead gets
the looked-up simulated response of the case's *first* attacker tool (truncated to 500
chars) -- this is what makes `sensitive_data_exposure` derivable from the args themselves
rather than asserted from the label.

## Label derivation (derivation `injecagent-1.0.0`)

All eleven `RiskDimension`s are always present.

| dimension | source |
|---|---|
| `prompt_injection_influence` | `not_applicable` for (a); `yes` for (b); `no` for (c) |
| `unauthorized_scope` | `no` for (a) (user tool is delegated); `yes` for every attacker call |
| `policy_conflict` | `yes` if any `injecagent_policies` predicate fires for the call's function+args, identical between (b) and (c) |
| `financial_commitment`, `destructive_or_irreversible_action` | `yes`/`no` from a fixed function-name set (`_FINANCIAL_COMMITMENT_FUNCTIONS`, `_DESTRUCTIVE_FUNCTIONS`) |
| `untrusted_destination`, `external_communication` | `yes` from another fixed function-name set, else `not_applicable` |
| `sensitive_data_exposure` | `yes` only for a ds case's terminal (exfiltration) attacker call, whose filled args carry the prior step's retrieved data; `not_applicable` for the dh dataset, for a ds case's first (read) attacker call, and for (a) |
| `privilege_escalation`, `insufficient_context`, `suspicious_action_sequence` | always `not_applicable` -- InjecAgent has no ground truth for any of these |

Destination `relationship`/`trust` are derived from text membership only, never from a
label: if a destination identifier appears in the user's own instruction it is
`known_third_party`/`principal`; if it instead appears in the example's own rendered
observation text it is `unknown_external`/`untrusted`; otherwise `unknown_external`/
`unknown`. Because (c)'s observation has the attacker instruction stripped out, an
attacker call's destination is `untrusted` in (b) and `unknown` in (c) even though the
proposed call and its arguments are identical -- an honest signal, not a leak, since (c)
truly gives the agent no textual basis for that destination.

## Function-name dimension sets

Derived by hand from `tools.json` names and one-line summaries for the 79 distinct
tool names that actually appear as a `User Tool` or `Attacker Tool` across both files
(see `_FINANCIAL_COMMITMENT_FUNCTIONS`, `_DESTRUCTIVE_FUNCTIONS`,
`_UNTRUSTED_DESTINATION_FUNCTIONS`, `_EXTERNAL_COMMUNICATION_FUNCTIONS`,
`_CHANGES_AUTHORITY_FUNCTIONS` in `injecagent.py`). All 17 user tools used across the
dataset are read-only (`Get*`/`Search*`/`Read*`/`View*`) and fall in none of these sets,
so none of these policies or dimensions ever fire on a benign (a) example.

## Known gaps

- **Attacker call arguments are synthetic, not InjecAgent's own.** InjecAgent evaluates
  a live agent and scores whatever arguments it actually produced; the raw case JSON
  gives us the attacker's *goal* (`Attacker Instruction`) and *tool name*, not concrete
  arguments. `fill_attacker_args`'s generic, type-based filling is a deterministic
  approximation, not a reproduction of any real agent trajectory.
- **`sensitive_data_exposure` payload is real InjecAgent data, but for an arbitrary
  argument combination.** `load_simulated_responses` picks the lexicographically first
  response recorded for a tool name across all of InjecAgent's own eval traces, since we
  don't know which argument combination "our" filled call would have produced.
- **`ToolFamily` has no health/social/physical-device bucket.** Toolkits like
  `The23andMe`, `Teladoc`, `EpicFHIR`, `DeepfakeGenerator`, `Terminal` fall back to
  `ToolFamily.MCP`; `ResourceKind` likewise has no health/person kind, so those
  toolkits' resources are `ResourceKind.OTHER`.
- **`OperationKind`/`ResourceKind` are inferred from the function name**, via keyword
  matching (`_infer_operation`, `_resource_kind`), not from any InjecAgent-native
  operation taxonomy (InjecAgent has none).
- **Only `test_cases_dh_base.json`/`test_cases_ds_base.json` are ported.** The
  `*_enhanced` variants, `user_cases.jsonl`, and `attacker_cases_{dh,ds}.jsonl` (the raw
  pools these base cases are assembled from) are not separately ported.
