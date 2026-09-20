# forecheck examples

Every script here runs offline in well under a second: none of them make a network
call or need a GPU. Run any of them with `uv run python examples/<name>.py` from the
repository root.

**The mock backend used throughout (`MockBackend`, wrapped by `LocalForecheck()`) is a
deterministic heuristic stand-in, not a trained model.** It exists so the SDK, the
middleware, and the policy engine can be exercised end-to-end without a checkpoint. Its
scores are not calibrated probabilities either, which is why a couple of the examples
build a trivial identity calibration bundle purely for demonstration purposes -- do not
copy that pattern into production code.

- **`sdk_quickstart.py`** — Constructs a `ForecheckClient` against an `httpx.MockTransport`
  backed by `LocalForecheck`, so it exercises the real HTTP request/response shapes.
  Calls `ready()`, `version()`, `classify()`, and `classify_and_evaluate()`.

- **`middleware_generic_agent.py`** — Wraps three fake tools with `guard_tool_calls` and
  runs a benign email-a-teammate scenario against an injected-instruction exfiltration
  scenario, printing the decision, matched rule ids, and policy bundle hash for each.

- **`mcp_interceptor.py`** — Wraps a fake in-memory MCP session with `guard_mcp_session`,
  calls a tool once, then mutates the tool's declared schema between calls to simulate a
  rug-pull and shows the interceptor recording it as an untrusted observation.

- **`openai_tools_adapter.py`** — Pure functions mapping an OpenAI Chat Completions
  `tool_calls[i]` entry (JSON-string arguments) into a `ProposedAction` and a full
  `ActionContext`, with an inline self-check.

- **`anthropic_tools_adapter.py`** — The same mapping for an Anthropic Messages API
  `tool_use` content block (already-parsed `input`), with an inline self-check.
