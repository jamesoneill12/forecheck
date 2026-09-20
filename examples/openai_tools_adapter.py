"""Map OpenAI Chat Completions ``tool_calls`` into forecheck's typed contract.

OpenAI represents a proposed tool call as
``{"id": ..., "type": "function", "function": {"name": ..., "arguments": "<json str>"}}``.
The functions below are pure and offline: they never call the OpenAI API, they just
translate that shape into a :class:`~forecheck.contracts.ProposedAction` and, given the
caller's own objective/principal/agent facts, a full
:class:`~forecheck.contracts.ActionContext`.
"""

from __future__ import annotations

import json
from typing import Any

from forecheck.contracts import ActionContext, ProposedAction
from forecheck.integrations.context_builder import ActionContextBuilder


def openai_tool_call_to_proposed_action(tool_call: dict[str, Any]) -> ProposedAction:
    function = tool_call["function"]
    arguments = json.loads(function["arguments"]) if function.get("arguments") else {}
    return ProposedAction(tool_name=function["name"], arguments=arguments)


def openai_tool_call_to_context(
    tool_call: dict[str, Any],
    *,
    objective_text: str,
    principal_id: str,
    agent_id: str,
    delegated_scopes: list[str] | None = None,
) -> ActionContext:
    proposed = openai_tool_call_to_proposed_action(tool_call)
    return (
        ActionContextBuilder()
        .objective(objective_text, explicit=True)
        .principal(principal_id)
        .agent(agent_id, delegated_scopes=delegated_scopes or [])
        .propose(proposed.tool_name, arguments=proposed.arguments)
        .build()
    )


def _self_check() -> None:
    tool_call = {
        "id": "call_1",
        "type": "function",
        "function": {"name": "get_weather", "arguments": '{"city": "Dublin"}'},
    }
    proposed = openai_tool_call_to_proposed_action(tool_call)
    if proposed.tool_name != "get_weather" or proposed.arguments != {"city": "Dublin"}:
        raise AssertionError("openai adapter produced an unexpected ProposedAction")

    context = openai_tool_call_to_context(
        tool_call,
        objective_text="What's the weather in Dublin?",
        principal_id="user-1",
        agent_id="agent-1",
        delegated_scopes=["weather:read"],
    )
    if context.proposed_action.tool_name != "get_weather":
        raise AssertionError("openai adapter produced an unexpected ActionContext")
    print("openai adapter self-check passed:", context.proposed_action)


if __name__ == "__main__":
    _self_check()
