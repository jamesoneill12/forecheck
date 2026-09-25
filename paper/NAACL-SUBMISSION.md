# NAACL 2027 submission notes

Target: NAACL 2027 (San Francisco, 2027-06-01 to 05) via ACL Rolling Review, October 2026
cycle. Submission deadline 2026-10-12 AoE; commitment 2026-12-23; notification 2027-02-10;
camera-ready 2027-03-03. Candidate track: special theme "Language as a Medium for Agentic
Communication", otherwise the safety/ethics or NLP-applications area.

## Build

- `paper/naacl.tex` is the ARR/NAACL version (`acl.sty` + `acl_natbib.bst`, unmodified copies
  of github.com/acl-org/acl-style-files). Build with `paper/build_naacl.sh`.
- `paper/lineno.sty` is lineno v5.9 vendored from github.com/latex-lineno/lineno. TeX Live's
  v5.7 misplaces the review-mode line numbers (right-column numbers land inside the left
  column); v5.9 puts them in the outer margins as in official ARR PDFs. Remove it if the
  submission build environment already ships v5.9 or later.
- Body figures are produced by `scripts/paper_figures.py` (`uv run python scripts/paper_figures.py`),
  which also regenerates the appendix figures.
- `paper/main.tex` is the earlier ICLR-workshop layout of the same sections; `make` builds it.
  Do not submit both anywhere (ARR forbids dual submission).
- Sections, appendix, and refs are shared between the two main files.

## Format checklist (ARR / NAACL long paper)

- [x] 8 pages of content, two-column `acl` style, 11pt Times: body ends on page 8 of `naacl.pdf`.
- [x] Limitations section present, unnumbered, after the conclusion, outside the page count.
- [x] Ethics statement present, unnumbered, outside the page count.
- [x] References unlimited; appendices after references, outside the count; nothing critical
      lives only in an appendix (every appendix table has a main-body pointer).
- [x] `\usepackage[review]{acl}` (line numbers, anonymous). Switch to `[final]` at camera-ready
      and add the author block; camera-ready may use 9 pages.
- [x] Anonymised: no author names, affiliations, repo URLs, or `docs/...`/`scripts/...` paths
      in the PDF. `grep -rn -i "intercom\|jamesoneill\|docs/\|scripts/" paper/sections paper/appendix.tex paper/naacl.tex` returns nothing.
- [ ] `inconsolata` package is commented out because it is not installed locally; re-enable
      if the submission build environment has it (cosmetic only).
- [ ] Responsible NLP checklist (filled in on the OpenReview form, not in the PDF). Answers to
      prepare: limitations = yes (section present); risks = yes (ethics statement); artifacts
      used = AgentDojo, InjecAgent, Granite 3.3, ModernBERT, granite-embedding-r2, Granite
      Guardian 3.3, gpt-oss-safeguard, gpt-5.6-sol (judge); artifacts created = synthetic
      generator + LoRA checkers, released Apache-2.0 on acceptance; compute = single B200
      node per run (report GPU-hours from run logs); seeds/variance = stated in Limitations;
      human subjects = none; AI assistance = code and writing assistance disclosed.
- [ ] All authors need OpenReview profiles with ORCID before 2026-10-12, and ARR asks each
      author to be available to review.
- [ ] Data/code release statement in the submission form: code and generator released on
      acceptance; external benchmark derivations released as scripts, not redistributed data.

## Sixth review (2026-09-24) and status

Reviewer-6 file: /tmp/fc-review/reviewer-6.md. Landed: §2 dimension fix, agent-self
sentence, 11-row Appendix A table, experimental-details appendix, system comparison
table, self-judgment demoted, composition compressed, symbolic baseline row, Guardian
numbers withdrawn (verdict-position bug, commit 1a3cd4e), `eval-guardian-fixed` (corrected
verdict-position read, all Guardian numbers replaced), `eval-injecagent-controls` (done:
length-matched padded/instruction controls close the InjecAgent pair-test length
confound, Table~\ref{tab:external} and Table~\ref{tab:injecagent-controls}),
single-factor v6a/v6b arms (done: key removal is the whole AgentDojo injection gain,
`docs/results/synthetic-v2/README.md` "v6a / v6b" and Table~\ref{tab:agentdojo}), per-kind
`policy_conflict` attribution (done: `docs/results/synthetic-v2/per-kind/per_kind_auprc.md`
and Table~\ref{tab:per-kind}).

## Open experiments the reviewers asked for (all cheap)

1. **Done.** Length-matched InjecAgent clean control (`eval-injecagent-controls`):
   padded and instruction controls, byte-matched to the poisoned observation length;
   v6 wins 0.98--0.99 tie-adjusted against both, v4's 0.62 falls to 0.51 (chance)
   against padded. See `docs/results/injecagent/README.md` and
   Table~\ref{tab:injecagent-controls}.
2. **Done.** Single-factor v6 arms: key removed with short observations (v6a); key kept
   with long observations (v6b). v6a reproduces most of v6's AgentDojo injection gain
   (0.659 vs.\ 0.693), v6b reproduces v4's failure (0.139 vs.\ 0.128 base); the gain is the
   key removal, not observation length. See `docs/results/synthetic-v2/README.md`.
3. AgentDojo payload-deletion counterfactual with the call held fixed (inference only).
4. Blind judge and agent-self re-run on v6 text (one API job, one inference pass).
5. Within-arm temperature perturbation of the decoder for the composition attribution (CPU).
6. Compiled-predicate symbolic baseline for `unauthorized_scope`, `privilege_escalation`, and
   seen-kind `policy_conflict` (CPU).
7. Guardian positive control on its native risk categories, plus one dumped rendered prompt.
8. **Done.** Per-withheld-kind AUPRC on the kind split: pooled score understates
   within-kind ranking; residual failure concentrates in the daily-quota and
   classification-threshold kinds. See `docs/results/synthetic-v2/per-kind/per_kind_auprc.md`
   and Table~\ref{tab:per-kind}. AUPRC split by `action_origin` on synthetic injection and
   bootstrap CIs on synthetic tables (needs per-example dumps from FSx) remain open.
9. **Done.** Scaling curve + full FT: 2B LoRA at 5k/25k/100k/250k v6-generator rows and
   one 2B full-parameter fine-tune at 25k. Synthetic scores are flat; external transfer
   falls monotonically with more rows and full fine-tuning recovers most of it. See
   `docs/results/synthetic-v2/README.md`, Figure~\ref{fig:scaling}, and
   Table~\ref{tab:scaling}.
