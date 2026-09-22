"""Backends and the prompt contract that turn an ActionContext into raw scores."""

from __future__ import annotations

from forecheck.inference.agent_self import (
    AgentSelfBackend,
    AgentSelfBackendConfig,
    load_agent_self_config,
)
from forecheck.inference.base import BackendCapabilities, BaseBackend, ClassifierBackend, RawScores
from forecheck.inference.classifier import AbstainPolicy, Classifier
from forecheck.inference.encoder import EncoderBackend, EncoderBackendConfig
from forecheck.inference.guardian import (
    GuardianBackend,
    GuardianBackendConfig,
    GuardianFamily,
    load_guardian_config,
)
from forecheck.inference.hf import HFBackend, HFBackendConfig
from forecheck.inference.mock import MockBackend
from forecheck.inference.prompt import (
    PROMPT_CONTRACT_HASH,
    QUESTIONS,
    prompt_contract_hash,
    serialization_contract_hash,
)
from forecheck.inference.serialization import SerializedContext, render_context, serialize_context

__all__ = [
    "PROMPT_CONTRACT_HASH",
    "QUESTIONS",
    "AbstainPolicy",
    "AgentSelfBackend",
    "AgentSelfBackendConfig",
    "BackendCapabilities",
    "BaseBackend",
    "Classifier",
    "ClassifierBackend",
    "EncoderBackend",
    "EncoderBackendConfig",
    "GuardianBackend",
    "GuardianBackendConfig",
    "GuardianFamily",
    "HFBackend",
    "HFBackendConfig",
    "MockBackend",
    "RawScores",
    "SerializedContext",
    "load_agent_self_config",
    "load_guardian_config",
    "prompt_contract_hash",
    "render_context",
    "serialization_contract_hash",
    "serialize_context",
]
