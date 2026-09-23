# Injection label leak in the synthetic generator (v1 to v5)

Date: 2026-09-23. Trigger: the 2B v4 checker scored below the base rate on
`prompt_injection_influence` on AgentDojo banking (AUPRC 0.128 at a 0.150 positive
rate), while scoring 0.80 AUPRC on synthetic test. (An earlier version of this note said a
key-presence detector would score 1.0 there; that was wrong, see "Ceiling" below.) The
per-example score dump showed
the 2B injection head never fires on AgentDojo (raw logits in [-5.0, -3.0]).

## Measurement

Contrast of the rendered call between injected-instruction examples
(`latent.action_origin == injected_instruction`, n=832) and all other examples
(n=12,480) over the v4 `test`, `heldout_family`, `heldout_policy_kind` splits:

| cue in `proposed_action.arguments` | injected | not injected |
|---|---|---|
| key `instructed_target` present | 1.00 | 0.00 |
| key `to` present | 1.00 | 0.03 |
| substring `attacker` in any argument value | 0.59 | 0.00 |
| substring `shadow` | 0.19 | 0.00 |
| substring `external-support` | 0.21 | 0.00 |
| substring `routing-acct` | 0.20 | 0.00 |
| substring `-007` | 0.20 | 0.00 |

Every other argument key has equal presence rates (within 0.02) across the two groups.

Observation text: injected observations are one of five short templates (median 132
characters) whose last clause is the instruction, with a target drawn from a pool of
five literals, three of which contain the word "attacker". AgentDojo's injected
observations are 2,000-character record dumps with the instruction in one field.

Source: `src/forecheck/data/rendering.py`, `_build_arguments` (line 571-573 at
commit `db935d3`) writes `args["to"] = surface.injected_target` and
`args["instructed_target"] = surface.injected_target` whenever the scenario is an
injection; `_INJECTION_INSTRUCTIONS` holds the five target literals.

## What this means for the reported numbers

- Every synthetic `prompt_injection_influence` result for v1 to v5 (decoder 2B and 8B,
  encoders, and the rule baseline where it reads argument keys) could have been produced
  by a key-presence detector. Those numbers are not evidence of injection detection.
- **Ceiling.** `_sample_action_origin` (`generation/scenarios.py:103`) draws the label from
  two origins: `INJECTED_INSTRUCTION` (p=0.06 when untrusted content is present, instruction
  rendered) and `COMPROMISED_TOOL_SCHEMA` (p=0.02, `untrusted_present=False`, nothing
  rendered). `_prompt_injection_influence` (`data/labeling.py:150`) returns YES for both. So
  about a quarter of synthetic positives carry no injected text, and a detector reading only
  the observation is capped near 0.75-0.80 AUPRC, the same place a key-only detector lands.
  The v4 (0.80) and v6 (0.79) synthetic scores measure that ceiling, not what the head reads.
  A key-presence detector does NOT score 1.0 (earlier versions of this note said so; the
  paper's 2026-09-23 reviewer pass caught it). An AUPRC split by `latent.action_origin`
  would show what the head reads and has not been computed.
- The LLM-judge agreement on this dimension (kappa 0.905, `docs/results/judge/`) is
  also inflated: the judge saw the same `instructed_target` argument.
- The AgentDojo result is the first measurement of injection detection without the
  leak: 2B v4 0.128 / 0.348 AUPRC / AUROC (fails), 8B v4 0.701 / 0.895 (partly
  transfers). The 8B result stands because the leak is absent from AgentDojo; the
  8B model learned something beyond the shortcut, the 2B model did not.
- The identity-ablation results are unaffected: those dimensions
  (`policy_conflict`, `unauthorized_scope`) do not use the leaked keys.

## Fix (generator v6)

Implemented in `src/forecheck/data/rendering.py` (renderer version 2.0.0):
`instructed_target` removed; target argument key chosen from the tool kind and filled
for every call of that kind, benign or injected; benign and injected targets drawn
from the same pools with no marker tokens; observations rendered as 300-2,000
character records, messages, page excerpts or listings for both injected and benign
content, with the instruction at a random position under one of many framings.
`scripts/check_no_leakage.py` now fails on any argument-key presence gap above 0.05
between injected and non-injected examples and on a token denylist.

## Result (v6 retrain, 2026-09-23)

Both sizes were retrained on v6 (49,996 rows; `check_no_leakage` passed: no
denylisted tokens, key-rate parity held). Synthetic `prompt_injection_influence`
AUPRC / AUROC on test barely moved: 0.802 / 0.901 (2B v4) to 0.788 / 0.893 (2B v6),
0.791 / 0.898 (8B v4) to 0.795 / 0.898 (8B v6) (`docs/results/synthetic-v2/README.md`).
The leak did not inflate the synthetic score; it changed what the head learned to
read. Zero-shot on AgentDojo banking, the same
dimension went from 0.128 / 0.348 (2B v4) to 0.693 / 0.928 (2B v6) and from
0.701 / 0.895 (8B v4) to 0.838 / 0.966 (8B v6) (`docs/results/agentdojo/README.md`).
The 2B v4 failure was the leak, not the model size: with the shortcut removed, the
2B head learned a signal that transfers to traces it never saw. Whether the v6
heads read the injected text itself, rather than the call, is the InjecAgent
paired test (`docs/results/injecagent/README.md`): 2B v6 puts the poisoned variant
above its clean twin on 97.7% of pairs, against 50.4% for 2B v4.

Retraining: `train-2b-b200-v6-recipe.yaml` and `train-8b-b200-v6-recipe.yaml`
regenerate the data, train, and evaluate on the synthetic splits and on AgentDojo
banking in the same job, so the synthetic and external injection numbers land
together.

## Lesson

Contrast the rendered surface between label groups before training, not after an
external evaluation fails. `check_no_leakage.py` existed but tested text overlap, not
argument-key presence. Any field written conditionally on a latent that determines a
label is a leak, however innocuous the name.
