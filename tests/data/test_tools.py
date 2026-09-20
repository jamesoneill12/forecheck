from __future__ import annotations

import pytest

from forecheck.contracts import OperationKind, ToolFamily
from forecheck.data.tools import TOOL_CATALOGUE, get_tool, tools_for_family


def test_catalogue_has_at_least_sixty_tools() -> None:
    assert len(TOOL_CATALOGUE) >= 60


def test_every_family_has_at_least_four_tools() -> None:
    for family in ToolFamily:
        tools = tools_for_family(family)
        assert len(tools) >= 4, f"{family} only has {len(tools)} tools"
        assert all(tool.family is family for tool in tools)


def test_tool_names_are_unique() -> None:
    names = [tool.name for tool in TOOL_CATALOGUE]
    assert len(names) == len(set(names))


def test_operations_are_mixed_across_the_catalogue() -> None:
    operations = {tool.operation for tool in TOOL_CATALOGUE}
    assert operations == set(OperationKind)


def test_get_tool_returns_known_tool() -> None:
    tool = get_tool("email.send_message")
    assert tool.name == "email.send_message"
    assert tool.is_communication is True


def test_get_tool_raises_on_unknown_name() -> None:
    with pytest.raises(KeyError):
        get_tool("does.not.exist")


def test_financial_tools_are_flagged_honestly() -> None:
    transfer = get_tool("payments.transfer_funds")
    assert transfer.is_financial is True
    assert transfer.intrinsically_irreversible is True

    read = get_tool("payments.read_invoice")
    assert read.is_financial is False
