"""Client-side integrations: SDK, in-process runner, and tool-call interceptors.

This package never imports :mod:`forecheck.api`. It speaks to a running forecheck
service over HTTP (:mod:`forecheck.integrations.sdk`) or runs the classifier and policy
engine in-process (:mod:`forecheck.integrations.local`), and it never defines a wire
type of its own -- everything here is built from :mod:`forecheck.contracts`.
"""

from __future__ import annotations

from forecheck.integrations.context_builder import ActionContextBuilder, ForecheckContextWarning
from forecheck.integrations.digest import argument_digest, canonical_json
from forecheck.integrations.local import LocalForecheck
from forecheck.integrations.mcp import McpSessionGuard, guard_mcp_session
from forecheck.integrations.middleware import (
    ToolCallArgumentsChanged,
    ToolCallDenied,
    guard_tool_calls,
    guard_tool_calls_async,
)
from forecheck.integrations.sdk import AsyncForecheckClient, ForecheckClient, ForecheckClientError

__all__ = [
    "ActionContextBuilder",
    "AsyncForecheckClient",
    "ForecheckClient",
    "ForecheckClientError",
    "ForecheckContextWarning",
    "LocalForecheck",
    "McpSessionGuard",
    "ToolCallArgumentsChanged",
    "ToolCallDenied",
    "argument_digest",
    "canonical_json",
    "guard_mcp_session",
    "guard_tool_calls",
    "guard_tool_calls_async",
]
