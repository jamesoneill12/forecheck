from __future__ import annotations

from datetime import UTC, datetime

import pytest

from forecheck.contracts import (
    ActionContext,
    ActionOrigin,
    AgentIdentity,
    AuthorizationBasis,
    Example,
    LabelSet,
    LabelValue,
    LatentScenario,
    OperationKind,
    Principal,
    ProposedAction,
    Provenance,
    RiskDimension,
    SourceLicense,
    Split,
    UsageRestriction,
    UserObjective,
)
from forecheck.data.tools import get_tool


class FakeTokenizer:
    """A minimal word-splitting stand-in for a real ``transformers`` tokenizer.

    Deterministic across calls within one instance: the same word always maps to the
    same id, and distinct words always map to distinct ids, which is all
    :mod:`forecheck.training.dataset` and :func:`forecheck.training.loss.resolve_candidate_ids`
    need from a tokenizer.
    """

    def __init__(self) -> None:
        self._vocab: dict[str, int] = {}

    def _id_for(self, token: str) -> int:
        return self._vocab.setdefault(token, len(self._vocab) + 1)

    def encode(self, text: str, add_special_tokens: bool = True) -> list[int]:
        words = text.split() or ["<empty>"]
        ids = [self._id_for(word) for word in words]
        if add_special_tokens:
            return [self._id_for("<bos>"), *ids]
        return ids

    @property
    def eos_token_id(self) -> int:
        return self._id_for("<eos>")

    @property
    def pad_token_id(self) -> int:
        return 0


class FakeChatTokenizer(FakeTokenizer):
    """A :class:`FakeTokenizer` with a real (non-merging) chat template, for exercising
    ``use_chat_template=True`` without a real tokenizer's ``apply_chat_template``."""

    def apply_chat_template(
        self,
        messages: list[dict[str, str]],
        *,
        add_generation_prompt: bool = True,
        tokenize: bool = False,
        **kwargs: object,
    ) -> str:
        system = next(m["content"] for m in messages if m["role"] == "system")
        user = next(m["content"] for m in messages if m["role"] == "user")
        text = f"<sys>{system}</sys><user>{user}</user>"
        if add_generation_prompt:
            text += "<assistant>"
        return text


@pytest.fixture
def fake_tokenizer() -> FakeTokenizer:
    return FakeTokenizer()


@pytest.fixture
def fake_chat_tokenizer() -> FakeChatTokenizer:
    return FakeChatTokenizer()


def make_training_example(
    example_id: str = "ex-1",
    *,
    split: Split | None = Split.TRAIN,
    usage: UsageRestriction = UsageRestriction.TRAIN_AND_EVAL,
    canary_present: bool = False,
    label_overrides: dict[RiskDimension, LabelValue] | None = None,
) -> Example:
    family_id = f"{example_id}-family"
    values = dict.fromkeys(RiskDimension, LabelValue.NO)
    values[RiskDimension.INSUFFICIENT_CONTEXT] = LabelValue.NOT_APPLICABLE
    if label_overrides:
        values.update(label_overrides)
    latent = LatentScenario(
        scenario_id=f"{example_id}-scenario",
        family_id=family_id,
        template_lineage=[family_id],
        tool=get_tool("email.read_message"),
        operation=OperationKind.READ,
        authorization_basis=AuthorizationBasis.EXPLICIT,
        action_origin=ActionOrigin.PRINCIPAL_REQUEST,
    )
    context = ActionContext(
        objective=UserObjective(text="Read the latest message in my inbox."),
        principal=Principal(id="user-1"),
        agent=AgentIdentity(id="agent-1", delegated_scopes=["email.read"]),
        proposed_action=ProposedAction(tool_name="email.read_message", arguments={}),
    )
    return Example(
        example_id=example_id,
        family_id=family_id,
        split=split,
        latent=latent,
        context=context,
        labels=LabelSet(values=values, derivation_version="test-1.0"),
        provenance=Provenance(
            generator_name="test",
            generator_version="1.0.0",
            seed=0,
            created_at=datetime.now(tz=UTC),
        ),
        license=SourceLicense(usage=usage, canary_present=canary_present),
    )


__all__ = [
    "FakeChatTokenizer",
    "FakeTokenizer",
    "fake_chat_tokenizer",
    "fake_tokenizer",
    "make_training_example",
]
