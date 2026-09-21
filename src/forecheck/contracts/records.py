"""On-disk dataset record schema.

One JSONL row is one :class:`Example`. Rows are self-describing: given a row alone you
can reconstruct which generator produced it, from which latent scenario, under which
transformation, against which label-derivation version, and under which licence.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forecheck.contracts.context import ActionContext
from forecheck.contracts.enums import LabelValue, RiskDimension, ToolFamily
from forecheck.contracts.latent import DifficultyTier, LatentScenario

__all__ = [
    "ContrastiveAxis",
    "DatasetManifest",
    "Example",
    "LabelSet",
    "Provenance",
    "SourceLicense",
    "Split",
    "Transformation",
    "UsageRestriction",
]

ShortStr = Annotated[str, Field(max_length=512)]

LABEL_SCHEMA_VERSION = "1.0"


class Split(StrEnum):
    TRAIN = "train"
    CALIBRATION = "calibration"
    DEV = "dev"
    TEST = "test"
    HELDOUT_FAMILY = "heldout_family"
    ADVERSARIAL = "adversarial"
    HELDOUT_POLICY_KIND = "heldout_policy_kind"
    HELDOUT_POLICY_PHRASING = "heldout_policy_phrasing"


class ContrastiveAxis(StrEnum):
    """The single causally relevant fact varied between the two halves of a pair."""

    PRINCIPAL_AUTHORIZATION = "principal_authorization"
    DESTINATION_TENANCY = "destination_tenancy"
    RESOURCE_SENSITIVITY = "resource_sensitivity"
    ENVIRONMENT_STAGE = "environment_stage"
    REVERSIBILITY = "reversibility"
    READ_VERSUS_WRITE = "read_versus_write"
    FINANCIAL_MATERIALITY = "financial_materiality"
    EXPLICIT_VERSUS_INFERRED_INTENT = "explicit_versus_inferred_intent"
    INSTRUCTION_PROVENANCE = "instruction_provenance"
    PERMISSION_VERSUS_ESCALATION = "permission_versus_escalation"
    ISOLATED_VERSUS_SEQUENCE = "isolated_versus_sequence"
    KNOWN_VERSUS_LOOKALIKE_DESTINATION = "known_versus_lookalike_destination"
    POLICY_PRESENT_VERSUS_ABSENT = "policy_present_versus_absent"
    SURFACE_PARAPHRASE = "surface_paraphrase"
    """Irrelevant change. Labels must NOT move; used for invariance testing."""


INVARIANT_AXES: frozenset[ContrastiveAxis] = frozenset({ContrastiveAxis.SURFACE_PARAPHRASE})


class UsageRestriction(StrEnum):
    TRAIN_AND_EVAL = "train_and_eval"
    EVAL_ONLY = "eval_only"
    UNKNOWN = "unknown"


class SourceLicense(BaseModel):
    """Licence provenance for any externally sourced content in this row.

    Rows generated wholly by forecheck carry ``source_name='forecheck-synthetic'``.
    Rows derived from a public benchmark carry that benchmark's terms, and
    ``EVAL_ONLY`` rows are refused by the training data loader.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_name: ShortStr = "forecheck-synthetic"
    source_url: ShortStr | None = None
    license_id: ShortStr = "Apache-2.0"
    usage: UsageRestriction = UsageRestriction.TRAIN_AND_EVAL
    attribution_required: bool = False
    canary_present: bool = False


class Provenance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    generator_name: ShortStr
    generator_version: ShortStr
    renderer: ShortStr = Field(
        default="template",
        description="'template' for the fully offline path, otherwise the model id.",
    )
    renderer_version: ShortStr = "n/a"
    render_prompt_hash: ShortStr | None = None
    seed: int
    created_at: datetime
    cost_usd: float = Field(default=0.0, ge=0.0)
    validator_versions: dict[ShortStr, ShortStr] = Field(default_factory=dict)


class Transformation(BaseModel):
    """How this row was derived from a base row, for contrastive pairs."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    axis: ContrastiveAxis
    base_example_id: ShortStr
    from_value: ShortStr
    to_value: ShortStr


class LabelSet(BaseModel):
    """Ground truth for every dimension, plus the code version that derived it."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    values: dict[RiskDimension, LabelValue]
    label_schema_version: ShortStr = LABEL_SCHEMA_VERSION
    derivation_version: ShortStr
    derived_from: ShortStr = "latent_scenario"

    @model_validator(mode="after")
    def _all_dimensions_present(self) -> LabelSet:
        missing = set(RiskDimension) - set(self.values)
        if missing:
            raise ValueError(f"label set is missing dimensions: {sorted(m.value for m in missing)}")
        return self

    def positives(self) -> frozenset[RiskDimension]:
        return frozenset(d for d, v in self.values.items() if v is LabelValue.YES)


class Example(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    example_id: ShortStr
    family_id: ShortStr
    split: Split | None = None

    latent: LatentScenario
    context: ActionContext
    labels: LabelSet

    provenance: Provenance
    license: SourceLicense = Field(default_factory=SourceLicense)

    contrastive_pair_id: ShortStr | None = None
    transformation: Transformation | None = None

    difficulty: DifficultyTier = DifficultyTier.MEDIUM
    tool_family: ToolFamily | None = None
    tags: list[ShortStr] = Field(default_factory=list)

    @model_validator(mode="after")
    def _family_matches_latent(self) -> Example:
        if self.family_id != self.latent.family_id:
            raise ValueError("example.family_id must equal latent.family_id")
        if self.transformation is not None and self.contrastive_pair_id is None:
            raise ValueError("a transformed example must carry its contrastive_pair_id")
        return self


class DatasetManifest(BaseModel):
    """Checksummed description of one split file."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    split: Split
    path: ShortStr
    n_examples: int = Field(ge=0)
    n_families: int = Field(ge=0)
    sha256: ShortStr
    label_schema_version: ShortStr = LABEL_SCHEMA_VERSION
    generator_versions: list[ShortStr] = Field(default_factory=list)
    created_at: datetime
    positive_rate: dict[RiskDimension, float] = Field(default_factory=dict)
    family_ids_sha256: ShortStr = Field(
        description="Digest of the sorted family id list, so leakage between splits "
        "can be detected without shipping the ids."
    )
