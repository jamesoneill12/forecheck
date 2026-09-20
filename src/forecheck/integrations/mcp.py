"""MCP interceptor.

Wraps an MCP client session (duck-typed: anything with ``list_tools()`` and
``call_tool(name, arguments)``; the real ``mcp.ClientSession`` qualifies without this
module importing the ``mcp`` package). Maps MCP tool metadata to
:class:`~forecheck.contracts.ProposedAction`, tracks a bounded trajectory and
observation history with honest trust labels, and implements the rug-pull check from
``docs/threat-model.md`` TM-11: a tool whose description or input schema changes
between calls gets its new digest recorded and an ``UNTRUSTED`` observation raised, so
the signal reaches the model rather than being silently absorbed.
"""

from __future__ import annotations

import inspect
from collections import deque
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

from forecheck.contracts import Decision, Limits, Observation, TrajectoryStep, TrustLevel
from forecheck.integrations.digest import argument_digest
from forecheck.integrations.middleware import ToolCallArgumentsChanged, ToolCallDenied

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    from forecheck.contracts import ActionContext, PolicyDecision

__all__ = ["McpSessionGuard", "ToolCallArgumentsChanged", "ToolCallDenied", "guard_mcp_session"]


def _default_on_review(decision: PolicyDecision, context: ActionContext) -> bool:
    return False


def _default_on_deny(decision: PolicyDecision) -> None:
    raise ToolCallDenied(decision)


async def _maybe_await(value: Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _get_any(obj: Any, *names: str) -> Any:
    for name in names:
        if isinstance(obj, Mapping):
            if name in obj:
                return obj[name]
            continue
        if hasattr(obj, name):
            return getattr(obj, name)
    return None


def _tool_name(tool: Any) -> str:
    name = _get_any(tool, "name")
    return str(name) if name is not None else "unknown"


def _tool_description(tool: Any) -> str | None:
    description = _get_any(tool, "description")
    return str(description) if description is not None else None


def _tool_input_schema(tool: Any) -> dict[str, Any]:
    schema = _get_any(tool, "inputSchema", "input_schema")
    return dict(schema) if isinstance(schema, Mapping) else {}


def _stringify_result(result: Any) -> str:
    content = _get_any(result, "content")
    text = str(content) if content is not None else str(result)
    return text[: Limits.MEDIUM_STR]


class McpSessionGuard:
    """Stateful wrapper around one MCP session. Construct via :func:`guard_mcp_session`."""

    def __init__(
        self,
        session: Any,
        forecheck: Any,
        *,
        context_factory: Callable[
            [str, dict[str, Any], Sequence[TrajectoryStep], Sequence[Observation]], ActionContext
        ],
        on_review: Callable[[PolicyDecision, ActionContext], bool] | None = None,
        on_deny: Callable[[PolicyDecision], None] | None = None,
        bundle: str | None = None,
        server: str | None = None,
    ) -> None:
        self._session = session
        self._forecheck = forecheck
        self._context_factory = context_factory
        self._review = on_review or _default_on_review
        self._deny = on_deny or _default_on_deny
        self._bundle = bundle
        self._server = server
        self._snapshots: dict[str, tuple[str | None, str]] = {}
        self._trajectory: deque[TrajectoryStep] = deque(maxlen=Limits.MAX_TRAJECTORY_STEPS)
        self._observations: deque[Observation] = deque(maxlen=Limits.MAX_OBSERVATIONS)
        self._next_index = 0

    @property
    def trajectory(self) -> tuple[TrajectoryStep, ...]:
        return tuple(self._trajectory)

    @property
    def observations(self) -> tuple[Observation, ...]:
        return tuple(self._observations)

    async def list_tools(self) -> list[Any]:
        raw = await _maybe_await(self._session.list_tools())
        tools = list(_get_any(raw, "tools") or raw)
        for tool in tools:
            name = _tool_name(tool)
            description = _tool_description(tool)
            schema = _tool_input_schema(tool)
            digest = argument_digest({"description": description or "", "input_schema": schema})
            self._snapshots.setdefault(name, (description, digest))
        return tools

    async def _check_schema_drift(self, name: str) -> tuple[str | None, str | None, bool]:
        tools = await self.list_tools()
        live = next((t for t in tools if _tool_name(t) == name), None)
        if live is None:
            return (None, None, False)
        description = _tool_description(live)
        schema = _tool_input_schema(live)
        digest = argument_digest({"description": description or "", "input_schema": schema})
        baseline = self._snapshots.get(name)
        changed = baseline is not None and baseline[1] != digest
        self._snapshots[name] = (description, digest)
        return (description, digest, changed)

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        description, schema_digest, changed = await self._check_schema_drift(name)
        if changed:
            self._observations.append(
                Observation(
                    id=f"obs-schema-{name}-{len(self._observations)}",
                    source=f"mcp:{self._server or 'unknown'}:{name}",
                    trust=TrustLevel.UNTRUSTED,
                    content=f"tool schema changed for {name!r} since it was first observed",
                )
            )

        context = self._context_factory(
            name, arguments, tuple(self._trajectory), tuple(self._observations)
        )
        proposed = context.proposed_action
        updates: dict[str, Any] = {}
        if schema_digest is not None:
            updates["tool_schema_digest"] = schema_digest
        if self._server is not None:
            updates["server"] = self._server
        if description is not None and proposed.tool_description is None:
            updates["tool_description"] = description
        if updates:
            context = context.model_copy(
                update={"proposed_action": proposed.model_copy(update=updates)}
            )

        classified_digest = argument_digest(context.proposed_action.arguments)
        decision = await _maybe_await(
            self._forecheck.classify_and_evaluate(context, bundle=self._bundle)
        )

        if decision.decision is Decision.DENY:
            self._deny(decision)
            return None
        if decision.decision is Decision.REVIEW and not self._review(decision, context):
            self._deny(decision)
            return None

        actual_digest = argument_digest(arguments)
        if actual_digest != classified_digest:
            raise ToolCallArgumentsChanged(name, classified_digest, actual_digest)

        result = await _maybe_await(self._session.call_tool(name, arguments))
        summary = _stringify_result(result)
        self._trajectory.append(
            TrajectoryStep(
                index=self._next_index,
                tool_name=name,
                arguments=arguments,
                arguments_digest=actual_digest,
                result_summary=summary,
                result_trust=TrustLevel.UNTRUSTED,
            )
        )
        self._next_index += 1
        self._observations.append(
            Observation(
                id=f"obs-result-{name}-{len(self._observations)}",
                source=f"mcp:{self._server or 'unknown'}:{name}",
                trust=TrustLevel.UNTRUSTED,
                content=summary,
            )
        )
        return result


def guard_mcp_session(
    session: Any,
    forecheck: Any,
    *,
    context_factory: Callable[
        [str, dict[str, Any], Sequence[TrajectoryStep], Sequence[Observation]], ActionContext
    ],
    on_review: Callable[[PolicyDecision, ActionContext], bool] | None = None,
    on_deny: Callable[[PolicyDecision], None] | None = None,
    bundle: str | None = None,
    server: str | None = None,
) -> McpSessionGuard:
    """Wrap ``session`` (an MCP ``ClientSession`` or a duck-typed equivalent) so every
    ``call_tool`` is classified and policy-checked first, with tool-schema-drift
    detection for the rug-pull threat (TM-11)."""
    return McpSessionGuard(
        session,
        forecheck,
        context_factory=context_factory,
        on_review=on_review,
        on_deny=on_deny,
        bundle=bundle,
        server=server,
    )
