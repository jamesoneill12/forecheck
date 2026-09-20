from __future__ import annotations

from collections import deque
from typing import Any

import pytest

from forecheck.contracts import Decision, Limits, PolicyDecision, ProposedAction
from forecheck.integrations.middleware import (
    ToolCallArgumentsChanged,
    ToolCallDenied,
    guard_tool_calls,
    guard_tool_calls_async,
)

from .conftest import make_context


def make_decision(decision: Decision, *, rule_ids: list[str] | None = None) -> PolicyDecision:
    return PolicyDecision(
        decision=decision,
        matched_rules=[],
        policy_bundle_id="test-bundle",
        policy_bundle_hash="deadbeef",
    )


class FakeForecheck:
    def __init__(self, decisions: list[PolicyDecision]) -> None:
        self._decisions = deque(decisions)
        self.calls: list[Any] = []

    def classify_and_evaluate(self, context: Any, *, bundle: str | None = None) -> PolicyDecision:
        self.calls.append((context, bundle))
        return self._decisions.popleft()


class FakeAsyncForecheck:
    def __init__(self, decisions: list[PolicyDecision]) -> None:
        self._decisions = deque(decisions)

    async def classify_and_evaluate(
        self, context: Any, *, bundle: str | None = None
    ) -> PolicyDecision:
        return self._decisions.popleft()


def default_context_factory(tool_name: str, args: dict[str, Any], history: Any) -> Any:
    return make_context(proposed_action=ProposedAction(tool_name=tool_name, arguments=args))


def test_allow_executes_and_records_history() -> None:
    forecheck = FakeForecheck([make_decision(Decision.ALLOW)])
    call_log: list[tuple[str, dict[str, Any]]] = []

    def call_tool(name: str, args: dict[str, Any]) -> str:
        call_log.append((name, args))
        return "ok"

    guarded = guard_tool_calls(call_tool, forecheck, context_factory=default_context_factory)
    result = guarded("search", {"q": "hi"})
    assert result == "ok"
    assert call_log == [("search", {"q": "hi"})]


def test_review_defaults_to_deny() -> None:
    forecheck = FakeForecheck([make_decision(Decision.REVIEW)])
    guarded = guard_tool_calls(
        lambda name, args: "should-not-run", forecheck, context_factory=default_context_factory
    )
    with pytest.raises(ToolCallDenied):
        guarded("search", {"q": "hi"})


def test_review_approved_executes() -> None:
    forecheck = FakeForecheck([make_decision(Decision.REVIEW)])
    guarded = guard_tool_calls(
        lambda name, args: "ran",
        forecheck,
        context_factory=default_context_factory,
        on_review=lambda decision, context: True,
    )
    assert guarded("search", {"q": "hi"}) == "ran"


def test_deny_raises_by_default() -> None:
    forecheck = FakeForecheck([make_decision(Decision.DENY)])
    guarded = guard_tool_calls(
        lambda name, args: "should-not-run", forecheck, context_factory=default_context_factory
    )
    with pytest.raises(ToolCallDenied) as exc_info:
        guarded("search", {"q": "hi"})
    assert exc_info.value.decision.decision is Decision.DENY


def test_deny_uses_custom_on_deny() -> None:
    forecheck = FakeForecheck([make_decision(Decision.DENY)])
    seen: list[PolicyDecision] = []
    guarded = guard_tool_calls(
        lambda name, args: "should-not-run",
        forecheck,
        context_factory=default_context_factory,
        on_deny=seen.append,
    )
    assert guarded("search", {"q": "hi"}) is None
    assert len(seen) == 1


def test_argument_mismatch_before_execution_is_refused() -> None:
    forecheck = FakeForecheck([make_decision(Decision.ALLOW)])

    def mismatched_context_factory(tool_name: str, args: dict[str, Any], history: Any) -> Any:
        return make_context(proposed_action={"tool_name": tool_name, "arguments": {"q": "other"}})

    guarded = guard_tool_calls(
        lambda name, args: "should-not-run", forecheck, context_factory=mismatched_context_factory
    )
    with pytest.raises(ToolCallArgumentsChanged):
        guarded("search", {"q": "hi"})


def test_trajectory_is_bounded() -> None:
    n_calls = Limits.MAX_TRAJECTORY_STEPS + 5
    forecheck = FakeForecheck([make_decision(Decision.ALLOW) for _ in range(n_calls)])
    observed_lengths: list[int] = []

    def context_factory(tool_name: str, args: dict[str, Any], history: Any) -> Any:
        observed_lengths.append(len(tuple(history)))
        return make_context(proposed_action=ProposedAction(tool_name=tool_name, arguments=args))

    guarded = guard_tool_calls(lambda name, args: "ok", forecheck, context_factory=context_factory)
    for i in range(n_calls):
        guarded("search", {"q": str(i)})
    assert max(observed_lengths) <= Limits.MAX_TRAJECTORY_STEPS


async def test_async_allow_executes() -> None:
    forecheck = FakeAsyncForecheck([make_decision(Decision.ALLOW)])

    async def call_tool(name: str, args: dict[str, Any]) -> str:
        return "ok"

    guarded = guard_tool_calls_async(call_tool, forecheck, context_factory=default_context_factory)
    result = await guarded("search", {"q": "hi"})
    assert result == "ok"


async def test_async_deny_raises() -> None:
    forecheck = FakeAsyncForecheck([make_decision(Decision.DENY)])

    async def call_tool(name: str, args: dict[str, Any]) -> str:
        return "should-not-run"

    guarded = guard_tool_calls_async(call_tool, forecheck, context_factory=default_context_factory)
    with pytest.raises(ToolCallDenied):
        await guarded("search", {"q": "hi"})
