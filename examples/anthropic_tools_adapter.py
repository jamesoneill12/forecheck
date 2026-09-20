"""Map Anthropic Messages API ``tool_use`` content blocks into forecheck's contract.

Anthropic represents a proposed tool call as
``{"type": "tool_use", "id": ..., "name": ..., "input": {...}}`` (``input`` is already a
parsed object, unlike OpenAI's JSON-string ``arguments``). The functions below are pure
and offline: they never call the Anthropic API.
"""

from __future__ import annotations

from typing import Any

from forecheck.contracts import ActionContext, ProposedAction
from forecheck.integrations.context_builder import ActionContextBuilder


def anthropic_tool_use_to_proposed_action(block: dict[str, Any]) -> ProposedAction:
    if block.get("type") != "tool_use":
        raise ValueError(f"expected a 'tool_use' content block, got {block.get('type')!r}")
    return ProposedAction(tool_name=block["name"], arguments=dict(block.get("input") or {}))


def anthropic_tool_use_to_context(
    block: dict[str, Any],
    *,
    objective_text: str,
    principal_id: str,
    agent_id: str,
    delegated_scopes: list[str] | None = None,
) -> ActionContext:
    proposed = anthropic_tool_use_to_proposed_action(block)
    return (
        ActionContextBuilder()
        .objective(objective_text, explicit=True)
        .principal(principal_id)
        .agent(agent_id, delegated_scopes=delegated_scopes or [])
        .propose(proposed.tool_name, arguments=proposed.arguments)
        .build()
    )


def _self_check() -> None:
    block = {
        "type": "tool_use",
        "id": "toolu_1",
        "name": "get_weather",
        "input": {"city": "Dublin"},
    }
    proposed = anthropic_tool_use_to_proposed_action(block)
    if proposed.tool_name != "get_weather" or proposed.arguments != {"city": "Dublin"}:
        raise AssertionError("anthropic adapter produced an unexpected ProposedAction")

    context = anthropic_tool_use_to_context(
        block,
        objective_text="What's the weather in Dublin?",
        principal_id="user-1",
        agent_id="agent-1",
        delegated_scopes=["weather:read"],
    )
    if context.proposed_action.tool_name != "get_weather":
        raise AssertionError("anthropic adapter produced an unexpected ActionContext")
    print("anthropic adapter self-check passed:", context.proposed_action)


if __name__ == "__main__":
    _self_check()
