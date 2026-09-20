"""Tests for the OpenAI/Anthropic tool-call adapters that live under ``examples/``.

The adapters are pure functions with no forecheck-internal dependency beyond the
public contract, so they are loaded here straight from their file path rather than
duplicated into ``src/forecheck``.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

EXAMPLES_DIR = Path(__file__).resolve().parents[2] / "examples"


def _load_example_module(name: str) -> ModuleType:
    path = EXAMPLES_DIR / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"forecheck_example_{name}", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not load example module from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


openai_adapter = _load_example_module("openai_tools_adapter")
anthropic_adapter = _load_example_module("anthropic_tools_adapter")


def test_openai_tool_call_to_proposed_action_parses_json_arguments() -> None:
    tool_call = {
        "id": "call_1",
        "type": "function",
        "function": {"name": "send_email", "arguments": '{"to": "jane@acme.com"}'},
    }
    action = openai_adapter.openai_tool_call_to_proposed_action(tool_call)
    assert action.tool_name == "send_email"
    assert action.arguments == {"to": "jane@acme.com"}


def test_openai_tool_call_with_no_arguments() -> None:
    tool_call = {"function": {"name": "list_things", "arguments": ""}}
    action = openai_adapter.openai_tool_call_to_proposed_action(tool_call)
    assert action.arguments == {}


def test_openai_tool_call_to_context_builds_full_context() -> None:
    tool_call = {"function": {"name": "get_weather", "arguments": '{"city": "Dublin"}'}}
    context = openai_adapter.openai_tool_call_to_context(
        tool_call,
        objective_text="What's the weather?",
        principal_id="user-1",
        agent_id="agent-1",
        delegated_scopes=["weather:read"],
    )
    assert context.proposed_action.tool_name == "get_weather"
    assert context.agent.delegated_scopes == ["weather:read"]


def test_anthropic_tool_use_to_proposed_action_uses_input_directly() -> None:
    block = {"type": "tool_use", "id": "toolu_1", "name": "send_email", "input": {"to": "jane"}}
    action = anthropic_adapter.anthropic_tool_use_to_proposed_action(block)
    assert action.tool_name == "send_email"
    assert action.arguments == {"to": "jane"}


def test_anthropic_tool_use_rejects_wrong_block_type() -> None:
    with pytest.raises(ValueError, match="tool_use"):
        anthropic_adapter.anthropic_tool_use_to_proposed_action({"type": "text", "text": "hi"})


def test_anthropic_tool_use_to_context_builds_full_context() -> None:
    block = {"type": "tool_use", "name": "get_weather", "input": {"city": "Dublin"}}
    context = anthropic_adapter.anthropic_tool_use_to_context(
        block,
        objective_text="What's the weather?",
        principal_id="user-1",
        agent_id="agent-1",
    )
    assert context.proposed_action.tool_name == "get_weather"
    assert context.proposed_action.arguments == {"city": "Dublin"}
