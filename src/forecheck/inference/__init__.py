"""Backends and the prompt contract that turn an ActionContext into raw scores."""

from __future__ import annotations

from forecheck.inference.base import BackendCapabilities, BaseBackend, ClassifierBackend, RawScores
from forecheck.inference.classifier import AbstainPolicy, Classifier
from forecheck.inference.hf import HFBackend, HFBackendConfig
from forecheck.inference.mock import MockBackend
from forecheck.inference.prompt import PROMPT_CONTRACT_HASH, QUESTIONS, prompt_contract_hash
from forecheck.inference.serialization import SerializedContext, render_context, serialize_context

__all__ = [
    "PROMPT_CONTRACT_HASH",
    "QUESTIONS",
    "AbstainPolicy",
    "BackendCapabilities",
    "BaseBackend",
    "Classifier",
    "ClassifierBackend",
    "HFBackend",
    "HFBackendConfig",
    "MockBackend",
    "RawScores",
    "SerializedContext",
    "prompt_contract_hash",
    "render_context",
    "serialize_context",
]
