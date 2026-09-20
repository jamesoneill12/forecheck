"""Policy engine interface.

Hard constraints on every implementation of :class:`PolicyEngine`:

* It is a pure function of (scores, context facts, bundle). No network, no model, no
  clock read that changes the outcome, no randomness.
* It is total: every input yields a decision, and the default is the most restrictive
  decision the bundle declares.
* It is explainable by construction: the returned ``matched_rules`` reproduce the
  decision when replayed, and every rule carries the facts that fired it.
"""

from __future__ import annotations

import abc
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from forecheck.contracts import (
        ActionContext,
        ClassifyResponse,
        Decision,
        PolicyDecision,
    )

__all__ = ["PolicyEngine", "PolicyEngineBase"]


@runtime_checkable
class PolicyEngine(Protocol):
    @property
    def bundle_id(self) -> str: ...

    @property
    def bundle_hash(self) -> str: ...

    @property
    def default_decision(self) -> Decision: ...

    def evaluate(
        self, classification: ClassifyResponse, context: ActionContext | None = None
    ) -> PolicyDecision: ...


class PolicyEngineBase(abc.ABC):
    @property
    @abc.abstractmethod
    def bundle_id(self) -> str: ...

    @property
    @abc.abstractmethod
    def bundle_hash(self) -> str: ...

    @property
    @abc.abstractmethod
    def default_decision(self) -> Decision: ...

    @abc.abstractmethod
    def evaluate(
        self, classification: ClassifyResponse, context: ActionContext | None = None
    ) -> PolicyDecision: ...
