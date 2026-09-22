#!/usr/bin/env python3
"""Regenerate ``docs/data-card.md`` from the fixture manifests and code-level catalogues.

The data card must never drift from the code it describes, so every fact in it (label
rules, tool counts, axis/pattern/gap names, split sizes, hashes) is read live rather
than hand-copied. Run with ``uv run python scripts/gen_data_card.py``.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from forecheck.contracts import ContextGap, ContrastiveAxis, PolicyPredicateKind, SequencePattern
from forecheck.data.labeling import LABEL_DERIVATION_RULES
from forecheck.data.splitting import HELDOUT_PARAPHRASE_INDICES, HELDOUT_POLICY_KINDS
from forecheck.data.tools import TOOL_CATALOGUE

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "data" / "fixtures"
OUT_PATH = REPO_ROOT / "docs" / "data-card.md"


def _label_rules_section() -> str:
    lines = []
    for dimension, rule in LABEL_DERIVATION_RULES.items():
        lines.append(f"- **`{dimension.value}`**: {rule}")
    return "\n".join(lines)


def _tool_catalogue_section() -> str:
    counts = Counter(tool.family for tool in TOOL_CATALOGUE)
    lines = [f"Total tools: {len(TOOL_CATALOGUE)}.", "", "| Tool family | Count |", "| --- | --- |"]
    for family in sorted(counts, key=lambda f: f.value):
        lines.append(f"| `{family.value}` | {counts[family]} |")
    return "\n".join(lines)


def _enum_list(members: list[object]) -> str:
    return "\n".join(f"- `{member.value}`" for member in members)  # type: ignore[attr-defined]


def _policy_generalisation_section() -> str:
    kinds = "\n".join(f"- `{kind.value}`" for kind in PolicyPredicateKind)
    heldout_kinds = ", ".join(f"`{k.value}`" for k in sorted(HELDOUT_POLICY_KINDS))
    heldout_indices = ", ".join(str(i) for i in sorted(HELDOUT_PARAPHRASE_INDICES))
    return (
        f"{kinds}\n\n"
        f"`heldout_policy_kind` withholds {heldout_kinds} entirely from "
        "train/calibration/dev/test. `heldout_policy_phrasing` withholds clause "
        f"paraphrase index {{{heldout_indices}}} for every other (trained) kind from "
        "train. See ADR 0010 and ADR 0011."
    )


def _fixture_manifests() -> list[dict[str, Any]]:
    manifests = []
    for path in sorted(FIXTURES_DIR.glob("*.manifest.json")):
        manifests.append(json.loads(path.read_text()))
    return manifests


def _fixture_section(manifests: list[dict[str, Any]]) -> str:
    lines = [
        "| Split | Examples | Families | sha256 |",
        "| --- | --- | --- | --- |",
    ]
    for manifest in manifests:
        sha = str(manifest["sha256"])
        lines.append(
            f"| `{manifest['split']}` | {manifest['n_examples']} | "
            f"{manifest['n_families']} | `{sha[:16]}...` |"
        )
    lines.append("")
    lines.append("Per-dimension positive rate by split:")
    lines.append("")
    dims = list(LABEL_DERIVATION_RULES)
    header = "| Split | " + " | ".join(d.value for d in dims) + " |"
    sep = "| --- |" + " --- |" * len(dims)
    lines.append(header)
    lines.append(sep)
    for manifest in manifests:
        rates = manifest["positive_rate"]
        assert isinstance(rates, dict)
        row = [f"{rates.get(d.value, 0.0):.3f}" for d in dims]
        lines.append(f"| `{manifest['split']}` | " + " | ".join(row) + " |")
    return "\n".join(lines)


def build_card() -> str:
    manifests = _fixture_manifests()
    total_examples = sum(int(m["n_examples"]) for m in manifests)
    return f"""# forecheck synthetic data card

## Purpose

This dataset trains and evaluates forecheck's calibrated risk classifier for
proposed AI-agent tool actions. Every row is wholly synthetic: there is no real
user data, no real credentials, and no content sourced from an external benchmark.

## Generation method

Each `Example` is generated end-to-end from a randomly sampled `LatentScenario` via
`forecheck.generation.pipeline.GenerationPipeline`, using the offline template
renderer (`forecheck.generation.renderers.OfflineTemplateRenderer`), which never
makes a network call. Ground-truth labels are derived deterministically from the
latent scenario by `forecheck.data.labeling.derive_labels` -- never inferred from
the rendered text. Generation is seeded: the same master seed reproduces identical
`example_id`s and labels.

## Label derivation rules

Eleven risk dimensions, each derived by an explicit, total, pure function of the
latent scenario (verbatim from `forecheck.data.labeling.LABEL_DERIVATION_RULES`):

{_label_rules_section()}

## Tool catalogue

Every tool is a hand-authored, honest description of a plausible agent tool: its
family, operation, required scopes, and intrinsic properties (communication,
financial, authority-changing, irreversible, idempotent).

{_tool_catalogue_section()}

## Contrastive axes

Each contrastive pair varies exactly one causally relevant fact between its two
halves, holding everything else fixed, so the model cannot rely on a spurious
correlate of the intended cause:

{_enum_list(list(ContrastiveAxis))}

`surface_paraphrase` is an invariance axis: it deliberately does not change any
label and exists to test that irrelevant wording changes do not move predictions.

## Sequence patterns

Shape of the preceding trajectory a scenario can be embedded in:

{_enum_list(list(SequencePattern))}

Patterns prefixed `benign_*` exist so a positive `suspicious_action_sequence`
label is never inferable from trajectory length alone.

## Context gaps

A causally relevant fact can be deliberately withheld from the rendered example,
forcing the corresponding label(s) to `NOT_APPLICABLE` rather than a guess:

{_enum_list(list(ContextGap))}

## Policy predicate kinds

Each `PolicyPredicate` is evaluated against the latent scenario alone
(`forecheck.data.labeling.evaluate_predicate`), never against rendered text:

{_policy_generalisation_section()}

## Fixture splits

`data/fixtures/` contains {total_examples} examples split leakage-safely by
`forecheck.data.splitting.split_examples` (grouped by scenario-family / template
ancestry; both halves of a contrastive pair always land in the same split and
carry the same `contrastive_pair_id`).

{_fixture_section(manifests)}

## Licence

All rows carry `source_name='forecheck-synthetic'`
(`forecheck.contracts.records.SourceLicense`), licensed Apache-2.0 along with the
rest of this repository. No third-party or real user data is present.

## Known limitations

- The offline template renderer produces a bounded set of surface phrasings per
  scenario; it is not a substitute for held-out human or LLM-rendered evaluation
  data (see `evaluation_class=external_or_human` in `docs/evaluation-plan.md`).
- Tool catalogue coverage is representative, not exhaustive, of real agent
  ecosystems; new tool families require new hand-authored `ToolSpec` entries.
- `heldout_family` intentionally has skewed family coverage by construction (it
  exists to measure generalisation to an unseen tool family, not to be
  representative of the training distribution).

## Regeneration

```
uv run forecheck data generate --offline --config configs/data/fixtures.yaml --out data/fixtures
uv run forecheck data split data/fixtures
uv run forecheck data verify data/fixtures
uv run python scripts/gen_data_card.py
```

or `make fixtures && make data-card`.
"""


def main() -> int:
    if not FIXTURES_DIR.exists():
        print(f"fixtures directory not found: {FIXTURES_DIR}", file=sys.stderr)
        return 1
    OUT_PATH.write_text(build_card())
    print(f"wrote {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
