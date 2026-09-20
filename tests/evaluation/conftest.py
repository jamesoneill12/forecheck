"""Shared fixtures for the evaluation test suite.

Fixtures build :class:`~forecheck.contracts.Example` rows directly from
:mod:`forecheck.contracts`, without importing :mod:`forecheck.data` or
:mod:`forecheck.generation` (owned by a different, concurrently developed workstream).
This keeps the evaluation suite runnable standalone.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from forecheck.contracts import (
    ActionContext,
    AffectedResource,
    AgentIdentity,
    ContextGap,
    ContrastiveAxis,
    Destination,
    DifficultyTier,
    Example,
    LabelSet,
    LabelValue,
    LatentScenario,
    ModelInfo,
    Observation,
    OperationKind,
    PolicyStatement,
    Principal,
    ProposedAction,
    Provenance,
    ResourceKind,
    RiskDimension,
    Split,
    ToolFamily,
    ToolSpec,
    TrajectoryStep,
    Transformation,
    UserObjective,
)
from forecheck.inference.base import BackendCapabilities, RawScores
from forecheck.version import LABEL_DERIVATION_VERSION

if TYPE_CHECKING:
    from forecheck.contracts import ClassifyResponse, PolicyDecision

__all__ = [
    "StubBackend",
    "StubPolicyEngine",
    "all_no_labels",
    "make_example",
]


def all_no_labels(**overrides: LabelValue) -> dict[RiskDimension, LabelValue]:
    values = dict.fromkeys(RiskDimension, LabelValue.NO)
    values.update(overrides)
    return values


def make_example(
    example_id: str = "ex-1",
    family_id: str = "fam-1",
    *,
    labels: Mapping[RiskDimension, LabelValue] | None = None,
    tool_name: str = "email.send_message",
    tool_family: ToolFamily | None = ToolFamily.EMAIL_MESSAGING,
    difficulty: DifficultyTier = DifficultyTier.MEDIUM,
    split: Split | None = Split.TEST,
    trajectory: Sequence[TrajectoryStep] = (),
    observations: Sequence[Observation] = (),
    policies: Sequence[PolicyStatement] = (),
    resources: Sequence[AffectedResource] = (),
    destination: Destination | None = None,
    is_benign_hard_negative: bool = False,
    context_gaps: Sequence[ContextGap] = (),
    contrastive_pair_id: str | None = None,
    transformation: Transformation | None = None,
    objective_text: str = "Send the weekly status update to the team.",
    authorization_explicit: bool = True,
) -> Example:
    """Build a minimally valid, fully self-consistent :class:`Example`."""
    tool = ToolSpec(
        name=tool_name,
        family=tool_family or ToolFamily.EMAIL_MESSAGING,
        operation=OperationKind.CREATE,
        resource_kind=ResourceKind.MAILBOX,
        is_communication=True,
    )
    latent = LatentScenario(
        scenario_id=f"{example_id}-scenario",
        family_id=family_id,
        tool=tool,
        operation=OperationKind.CREATE,
        is_benign_hard_negative=is_benign_hard_negative,
        context_gaps=list(context_gaps),
        difficulty=difficulty,
    )
    context = ActionContext(
        objective=UserObjective(text=objective_text, authorization_explicit=authorization_explicit),
        principal=Principal(id="user-1"),
        agent=AgentIdentity(id="agent-1", delegated_scopes=["email.send"]),
        proposed_action=ProposedAction(tool_name=tool_name, tool_family=tool_family),
        trajectory=list(trajectory),
        observations=list(observations),
        policies=list(policies),
        resources=list(resources),
        destination=destination,
    )
    label_set = LabelSet(
        values=dict(labels) if labels is not None else all_no_labels(),
        derivation_version=LABEL_DERIVATION_VERSION,
    )
    provenance = Provenance(
        generator_name="test-fixture",
        generator_version="0.0.0",
        seed=0,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    return Example(
        example_id=example_id,
        family_id=family_id,
        split=split,
        latent=latent,
        context=context,
        labels=label_set,
        provenance=provenance,
        contrastive_pair_id=contrastive_pair_id,
        transformation=transformation,
        difficulty=difficulty,
        tool_family=tool_family,
    )


def make_paraphrase_pair(
    base_id: str = "base-1", pair_id: str = "pair-1", family_id: str = "fam-1"
) -> tuple[Example, Example]:
    """A base/transformed pair. Only the *transformed* row carries ``contrastive_pair_id``
    and ``transformation``; the base row is linked purely via ``transformation.base_example_id``,
    matching :class:`~forecheck.contracts.records.Example`'s own validator.
    """
    base = make_example(example_id=base_id, family_id=family_id)
    transformed = make_example(
        example_id=f"{base_id}-paraphrase",
        family_id=family_id,
        contrastive_pair_id=pair_id,
        transformation=Transformation(
            axis=ContrastiveAxis.SURFACE_PARAPHRASE,
            base_example_id=base_id,
            from_value="original wording",
            to_value="paraphrased wording",
        ),
        objective_text="Please send this week's status update to the team, thanks.",
    )
    return base, transformed


class StubBackend:
    """A minimal :class:`~forecheck.inference.base.ClassifierBackend` for tests.

    Scores every dimension at a fixed value unless overridden per-dimension, and can
    abstain on requested dimensions. Deterministic, no I/O.
    """

    def __init__(
        self,
        *,
        default_score: float = 0.5,
        scores_by_dimension: Mapping[RiskDimension, float] | None = None,
        abstain_on: frozenset[RiskDimension] = frozenset(),
    ) -> None:
        self._default_score = default_score
        self._scores_by_dimension = dict(scores_by_dimension) if scores_by_dimension else {}
        self._abstain_on = abstain_on
        self._model_info = ModelInfo(
            backend="stub",
            model_id="stub-v1",
            prompt_contract_hash="n/a",
            label_schema_version="1.0",
        )

    @property
    def model_info(self) -> ModelInfo:
        return self._model_info

    @property
    def capabilities(self) -> BackendCapabilities:
        return BackendCapabilities(supports_batching=True, deterministic=True)

    def score(
        self, context: ActionContext, dimensions: Sequence[RiskDimension] | None = None
    ) -> RawScores:
        from forecheck.contracts import TruncationInfo

        dims = list(dimensions) if dimensions is not None else list(RiskDimension)
        scores = {
            d: self._scores_by_dimension.get(d, self._default_score)
            for d in dims
            if d not in self._abstain_on
        }
        return RawScores(
            scores=scores, truncation=TruncationInfo(), abstained_dimensions=self._abstain_on
        )

    def score_batch(
        self,
        contexts: Sequence[ActionContext],
        dimensions: Sequence[RiskDimension] | None = None,
    ) -> list[RawScores]:
        return [self.score(c, dimensions) for c in contexts]

    def warmup(self) -> None:
        return None

    def close(self) -> None:
        return None


class StubPolicyEngine:
    """A minimal :class:`~forecheck.policies.base.PolicyEngine` for tests.

    Denies whenever any dimension's probability exceeds ``deny_threshold``, otherwise
    allows. No review branch, so tests can reason about false-allow/false-deny directly.
    """

    def __init__(self, deny_threshold: float = 0.9) -> None:
        self._deny_threshold = deny_threshold

    @property
    def bundle_id(self) -> str:
        return "stub-bundle"

    @property
    def bundle_hash(self) -> str:
        return "stub-hash"

    @property
    def default_decision(self) -> str:
        from forecheck.contracts import Decision

        return Decision.ALLOW

    def evaluate(
        self, classification: ClassifyResponse, context: ActionContext | None = None
    ) -> PolicyDecision:
        from forecheck.contracts import Decision, PolicyDecision

        deny = any(
            s.probability is not None and s.probability >= self._deny_threshold
            for s in classification.scores
        )
        return PolicyDecision(
            decision=Decision.DENY if deny else Decision.ALLOW,
            policy_bundle_id=self.bundle_id,
            policy_bundle_hash=self.bundle_hash,
        )
