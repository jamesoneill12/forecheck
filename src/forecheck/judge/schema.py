"""On-disk row schemas for the LLM-judge workflow (``forecheck judge sample|label|agreement``).

These are a separate, unversioned artifact family from :mod:`forecheck.contracts.records`
-- a judge run is a throwaway evaluation aid, not part of the dataset contract -- but they
follow the same conventions: frozen pydantic models, one JSON object per JSONL line.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from forecheck.contracts import DifficultyTier, LabelValue, RiskDimension, Split, ToolFamily

__all__ = [
    "JudgeDimensionVerdict",
    "JudgeLabelRow",
    "JudgeSampleRow",
    "read_sample_rows",
    "write_sample_rows",
]

JUDGE_LABEL_VALUES: frozenset[LabelValue] = frozenset(
    {LabelValue.YES, LabelValue.NO, LabelValue.NOT_APPLICABLE}
)


class JudgeSampleRow(BaseModel):
    """One example drawn by ``forecheck judge sample``, ready to hand to a judge model."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    example_id: str
    family_id: str
    split: Split | None
    tool_family: ToolFamily | None
    policy_kinds: tuple[str, ...] = Field(default_factory=tuple)
    difficulty: DifficultyTier
    rendered_full: str
    rendered_stripped: str
    generator_labels: dict[RiskDimension, LabelValue]


class JudgeDimensionVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    value: LabelValue
    rationale: str = ""


class JudgeLabelRow(BaseModel):
    """One judge verdict for one example, produced by ``forecheck judge label``.

    ``labels[dimension]`` is ``None`` when the judge's completion could not be parsed
    into a valid verdict for that dimension even after one retry; downstream consumers
    (``forecheck judge agreement``, ``forecheck evaluate --labels-from``) must treat
    that as :class:`~forecheck.contracts.LabelValue.UNDETERMINED`, never as a guess.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    example_id: str
    model: str
    provider: str
    strip_identity: bool
    labels: dict[RiskDimension, JudgeDimensionVerdict | None]
    parse_ok: bool
    retried: bool
    raw_completion: str
    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)
    cost_usd: float | None = None
    created_at: datetime
    error: str | None = None

    @property
    def cache_key(self) -> tuple[str, str, bool]:
        """``(model, example_id, strip_identity)`` -- the idempotency key ``label`` caches on."""
        return (self.model, self.example_id, self.strip_identity)


def read_sample_rows(path: Path) -> list[JudgeSampleRow]:
    if not path.exists():
        return []
    rows: list[JudgeSampleRow] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if stripped:
                rows.append(JudgeSampleRow.model_validate_json(stripped))
    return rows


def write_sample_rows(path: Path, rows: Sequence[JudgeSampleRow]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(row.model_dump_json())
            handle.write("\n")
