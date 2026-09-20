"""Generic tool-dispatch interceptor.

Wraps any ``call_tool(name, args) -> result`` callable so every call is classified and
policy-evaluated before it runs. This is deployment shape 1 from
``docs/product-spec.md`` §9: the only shape that closes the TOCTOU gap (TM-12) in
``docs/threat-model.md``, because the arguments classified are re-digested and checked
against the arguments about to execute.
"""

from __future__ import annotations

from collections import deque
from typing import TYPE_CHECKING, Any, Protocol

from forecheck.contracts import Decision, Limits, TrajectoryStep, TrustLevel
from forecheck.integrations.digest import argument_digest

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence

    from forecheck.contracts import ActionContext, PolicyDecision

__all__ = [
    "AsyncSupportsClassifyAndEvaluate",
    "SupportsClassifyAndEvaluate",
    "ToolCallArgumentsChanged",
    "ToolCallDenied",
    "guard_tool_calls",
    "guard_tool_calls_async",
]


class SupportsClassifyAndEvaluate(Protocol):
    def classify_and_evaluate(
        self, context: ActionContext, *, bundle: str | None = None
    ) -> PolicyDecision: ...


class AsyncSupportsClassifyAndEvaluate(Protocol):
    async def classify_and_evaluate(
        self, context: ActionContext, *, bundle: str | None = None
    ) -> PolicyDecision: ...


class ToolCallDenied(Exception):
    """Raised by the default ``on_deny`` handler when the policy decision is DENY, or
    when a REVIEW is not approved."""

    def __init__(self, decision: PolicyDecision) -> None:
        super().__init__(f"tool call denied by policy bundle {decision.policy_bundle_id!r}")
        self.decision = decision


class ToolCallArgumentsChanged(Exception):
    """Raised when the arguments about to execute no longer match the arguments that
    were classified: the TOCTOU check from TM-12 tripped."""

    def __init__(self, tool_name: str, expected_digest: str, actual_digest: str) -> None:
        super().__init__(
            f"arguments for tool {tool_name!r} changed between classification "
            f"({expected_digest}) and execution ({actual_digest})"
        )
        self.tool_name = tool_name
        self.expected_digest = expected_digest
        self.actual_digest = actual_digest


def _default_on_review(decision: PolicyDecision, context: ActionContext) -> bool:
    return False


def _default_on_deny(decision: PolicyDecision) -> None:
    raise ToolCallDenied(decision)


def guard_tool_calls(
    call_tool: Callable[[str, dict[str, Any]], Any],
    forecheck: SupportsClassifyAndEvaluate,
    *,
    context_factory: Callable[[str, dict[str, Any], Sequence[TrajectoryStep]], ActionContext],
    on_review: Callable[[PolicyDecision, ActionContext], bool] | None = None,
    on_deny: Callable[[PolicyDecision], None] | None = None,
    bundle: str | None = None,
) -> Callable[[str, dict[str, Any]], Any]:
    """Return a wrapped ``call_tool`` that classifies and policy-checks every call
    before it runs.

    ALLOW executes immediately. REVIEW calls ``on_review`` (default: reject). DENY (and
    a rejected REVIEW) calls ``on_deny`` (default: raise :class:`ToolCallDenied`).
    Immediately before execution the arguments are re-digested and compared against the
    digest computed at classification time; a mismatch raises
    :class:`ToolCallArgumentsChanged` instead of executing.
    """
    review = on_review or _default_on_review
    deny = on_deny or _default_on_deny
    history: deque[TrajectoryStep] = deque(maxlen=Limits.MAX_TRAJECTORY_STEPS)
    next_index = 0

    def guarded(tool_name: str, args: dict[str, Any]) -> Any:
        nonlocal next_index
        context = context_factory(tool_name, args, tuple(history))
        classified_digest = argument_digest(context.proposed_action.arguments)
        decision = forecheck.classify_and_evaluate(context, bundle=bundle)

        if decision.decision is Decision.DENY:
            deny(decision)
            return None
        if decision.decision is Decision.REVIEW and not review(decision, context):
            deny(decision)
            return None

        actual_digest = argument_digest(args)
        if actual_digest != classified_digest:
            raise ToolCallArgumentsChanged(tool_name, classified_digest, actual_digest)

        result = call_tool(tool_name, args)
        history.append(
            TrajectoryStep(
                index=next_index,
                tool_name=tool_name,
                arguments=args,
                arguments_digest=actual_digest,
                result_summary=str(result)[: Limits.MEDIUM_STR],
                result_trust=TrustLevel.UNTRUSTED,
            )
        )
        next_index += 1
        return result

    return guarded


def guard_tool_calls_async(
    call_tool: Callable[[str, dict[str, Any]], Awaitable[Any]],
    forecheck: AsyncSupportsClassifyAndEvaluate,
    *,
    context_factory: Callable[[str, dict[str, Any], Sequence[TrajectoryStep]], ActionContext],
    on_review: Callable[[PolicyDecision, ActionContext], bool] | None = None,
    on_deny: Callable[[PolicyDecision], None] | None = None,
    bundle: str | None = None,
) -> Callable[[str, dict[str, Any]], Awaitable[Any]]:
    """Async mirror of :func:`guard_tool_calls`. ``on_review``/``on_deny`` remain
    synchronous, since rejecting or denying does not itself need to await anything."""
    review = on_review or _default_on_review
    deny = on_deny or _default_on_deny
    history: deque[TrajectoryStep] = deque(maxlen=Limits.MAX_TRAJECTORY_STEPS)
    next_index = 0

    async def guarded(tool_name: str, args: dict[str, Any]) -> Any:
        nonlocal next_index
        context = context_factory(tool_name, args, tuple(history))
        classified_digest = argument_digest(context.proposed_action.arguments)
        decision = await forecheck.classify_and_evaluate(context, bundle=bundle)

        if decision.decision is Decision.DENY:
            deny(decision)
            return None
        if decision.decision is Decision.REVIEW and not review(decision, context):
            deny(decision)
            return None

        actual_digest = argument_digest(args)
        if actual_digest != classified_digest:
            raise ToolCallArgumentsChanged(tool_name, classified_digest, actual_digest)

        result = await call_tool(tool_name, args)
        history.append(
            TrajectoryStep(
                index=next_index,
                tool_name=tool_name,
                arguments=args,
                arguments_digest=actual_digest,
                result_summary=str(result)[: Limits.MEDIUM_STR],
                result_trust=TrustLevel.UNTRUSTED,
            )
        )
        next_index += 1
        return result

    return guarded
