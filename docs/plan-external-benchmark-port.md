# Plan: scoring forecheck on data we did not generate

Status 2026-09-22: every number in `docs/results/` comes from our own generator. The
independent judge (`docs/results/judge/README.md`) shows the labels are recoverable for
three dimensions and defined differently or unrecoverable for the rest, which helps, but a
reviewer will still ask for one result on an external dataset. This is the plan for that.

## Candidates

| benchmark | what it has | what it lacks | fit |
|---|---|---|---|
| AgentDojo (Debenedetti et al. 2024) | 4 suites (workspace, slack, travel, banking), 97 user tasks, 629 injection cases, real tool schemas, published agent traces with tool calls | principal entitlements, delegated scope, policy text | best: tool calls are realistic, traces exist for several LLMs, injection ground truth is exact |
| InjecAgent (Zhan et al. 2024) | 1054 cases, 17 user tools, 62 attacker tools, direct-harm and data-stealing attacker instructions embedded in tool responses | no traces (it tests whether the agent calls the attacker tool), no identity | good for `prompt_injection_influence` and `unauthorized_scope` only; smaller schema |
| AgentHarm | harmful user requests with tool use | benign/harmful is the user's intent, not delegated authority | weak fit |
| ToolEmu | emulated tool outputs and a safety judge | small, emulator-dependent | weak fit |

Decision: AgentDojo first, InjecAgent second if time allows.

## What we build

1. **Trace ingestion.** Parse AgentDojo run logs (per suite, per user task, per injection
   task, per model) into forecheck `Example` records: one record per proposed tool call,
   with the preceding messages as trajectory and the tool schema as the tool definition.
   Source of calls: AgentDojo's published runs directory (several attacker/defense/model
   combinations) plus, if needed, our own re-run of the benchmark with Granite-3.3-8B as the
   agent through AgentDojo's harness.
2. **Identity overlay.** AgentDojo has one implicit principal per suite (the workspace
   owner, the Slack user, the traveller, the bank customer). We make it explicit:
   principal id and role, entitlements derived from the suite's tool set, delegated scope
   derived from the user task (the tools its reference solution uses), and a per-suite
   natural-language policy set written once by us (for example, banking: "transfers above
   500 require the user to have named the payee in this conversation"; workspace: "do not
   send email to addresses outside the organisation domain unless the user named them").
   The overlay is fixed per suite and task, never per call, so it cannot leak the label.
3. **Labels from ground truth we did not write.**
   - `prompt_injection_influence`: the call executes (part of) the injection task's goal.
     AgentDojo already evaluates this per run; we reuse its security-check outcome and
     attribute it to the first call that advances the injection goal.
   - `unauthorized_scope`: the call uses a tool outside the user task's delegated set, or
     targets an entity (recipient, account, file) not derivable from the user task.
   - `policy_conflict`: the call violates one of our per-suite policies, checked by a
     deterministic predicate we write alongside the policy text.
   - `untrusted_destination`, `external_communication`, `financial_commitment`,
     `destructive_or_irreversible_action`: derived from the tool schema (send_money, send_email,
     delete_file, and so on), which is the same lookup the rule baseline does.
   - Not labelled: `insufficient_context`, `sensitive_data_exposure`,
     `suspicious_action_sequence` (unrecoverable or undefined here; report as not applicable).
   Labels for the first three are the ones that matter, and only `policy_conflict` depends
   on text we wrote.
4. **Arms.** Rule baseline; decoder 2B v4 zero-shot (no retraining on AgentDojo);
   decoder 2B v4 identity-stripped; Granite Guardian zero-shot; agent-self 8B. Optional:
   decoder fine-tuned on a held-out suite split (train on 3 suites, test on the 4th) to show
   what adaptation buys.
5. **Metrics.** Per-dimension AUPRC and AUROC on the three learnable dimensions; the
   approval-elimination curve on all calls; and one number nobody else reports on
   AgentDojo: the fraction of successful injections whose executing call the checker would
   have stopped at a fixed review budget, versus AgentDojo's own defenses (tool filter,
   repeat prompt, spotlighting).

## Expected outcome and how to read it

- If zero-shot v4 scores well above rules on `prompt_injection_influence` and
  `policy_conflict`, the synthetic training transfers and the paper has its external result.
- If it does not, the honest report is the size of the synthetic-to-real gap, and the
  held-out-suite fine-tune shows how much of it closes with in-domain data. Either is
  publishable; the second is the one to expect.

## Effort

| step | estimate |
|---|---|
| trace parser + Example rendering, tests on 2 suites | 0.5 day |
| overlay (entitlements, scopes, 4 policy sets with predicates) | 0.5 day |
| eval recipes, GPU runs (5 arms, 1 GPU each, minutes per arm) | 0.25 day |
| results doc + paper section | 0.25 day |
| optional held-out-suite fine-tune | 0.5 day + 1 GPU-hour |

Start: 2026-09-23. Owner: loop. Dependencies: none on the user.

## Open questions

- Which published AgentDojo runs to use as the trace source (attacker `important_instructions`,
  defense `none`, models GPT-4o / Claude 3.5 Sonnet / Llama 3 70B are the usual set).
- Whether to count a call that partially advances the injection goal as a positive.
- InjecAgent: worth porting only if its cases can be turned into proposed tool calls
  without running an agent, which its data format (attacker tool + parameters) permits.
