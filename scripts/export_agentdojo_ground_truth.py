#!/usr/bin/env python3
"""Export AgentDojo ground truth to ``data/external/agentdojo/ground_truth.json``.

AgentDojo's ``ground_truth(pre_environment)`` methods need a live environment instance
to run, which this script avoids by statically parsing the suite source with ``ast``
instead. This only recovers literal argument values (a class constant such as
``_ATTACKER_IBAN``, or a plain string/number), not values computed from the
environment (e.g. ``self.get_streaming_service(pre_environment)``). That is exactly
the "attacker literal" subset the labeller needs (recipient IBAN, hardcoded amount,
hardcoded date), so the limitation is not a problem for label derivation -- it is
documented in ``docs/external-agentdojo.md``.

Usage:
    uv run python scripts/export_agentdojo_ground_truth.py \\
        --agentdojo-root /tmp/agentdojo/src/agentdojo/default_suites/v1 \\
        --out data/external/agentdojo/ground_truth.json
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from pathlib import Path
from typing import Any

_UNRESOLVED = object()

DEFAULT_ROOT = Path("/tmp/agentdojo/src/agentdojo/default_suites/v1")  # noqa: S108 -- sparse checkout location
DEFAULT_OUT = Path("data/external/agentdojo/ground_truth.json")
SUITES = ["banking", "slack", "travel", "workspace"]

_TASK_CLASS_RE = re.compile(r"^(UserTask|InjectionTask)(\d+)$")


def _try_import_agentdojo() -> bool:
    """Best-effort check for an installable ``agentdojo``; never blocks the export.

    The real extraction path is always the static AST parse below, which is
    deterministic and testable without network access or a live environment.
    """
    try:
        result = subprocess.run(
            ["uv", "run", "--with", "agentdojo", "python", "-c", "import agentdojo"],
            capture_output=True,
            timeout=20,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def _resolve_node(node: ast.AST | None, consts: dict[str, Any]) -> Any:
    """Resolve an AST node to a literal value, or ``_UNRESOLVED`` if it depends on
    something only known at runtime (an environment lookup, a method call, ...)."""
    if node is None:
        return _UNRESOLVED
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant):
                parts.append(str(value.value))
            elif isinstance(value, ast.FormattedValue):
                resolved = _resolve_node(value.value, consts)
                if resolved is _UNRESOLVED:
                    return _UNRESOLVED
                parts.append(str(resolved))
            else:
                return _UNRESOLVED
        return "".join(parts)
    if (
        isinstance(node, ast.Attribute)
        and isinstance(node.value, ast.Name)
        and node.value.id == "self"
    ):
        return consts.get(node.attr, _UNRESOLVED)
    if isinstance(node, ast.Name) and node.id in consts:
        return consts[node.id]
    if isinstance(node, (ast.List, ast.Tuple)):
        values = []
        for elt in node.elts:
            resolved = _resolve_node(elt, consts)
            if resolved is _UNRESOLVED:
                return _UNRESOLVED
            values.append(resolved)
        return values
    try:
        return ast.literal_eval(node)
    except Exception:
        return _UNRESOLVED


def _class_body_constants(class_node: ast.ClassDef) -> dict[str, Any]:
    """Class-level ``NAME = <literal>`` assignments, resolved in source order so a
    later constant (``GOAL``) can reference an earlier one (``_ATTACKER_IBAN``)."""
    consts: dict[str, Any] = {}
    for stmt in class_node.body:
        target: str | None = None
        value_node: ast.AST | None = None
        if (
            isinstance(stmt, ast.Assign)
            and len(stmt.targets) == 1
            and isinstance(stmt.targets[0], ast.Name)
        ):
            target = stmt.targets[0].id
            value_node = stmt.value
        elif (
            isinstance(stmt, ast.AnnAssign)
            and isinstance(stmt.target, ast.Name)
            and stmt.value is not None
        ):
            target = stmt.target.id
            value_node = stmt.value
        if target is None:
            continue
        value = _resolve_node(value_node, consts)
        if value is not _UNRESOLVED:
            consts[target] = value
    return consts


def _dict_literal(node: ast.AST | None, consts: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(node, ast.Dict):
        return {}
    out: dict[str, Any] = {}
    for key_node, value_node in zip(node.keys, node.values, strict=True):
        if key_node is None:
            continue
        key = _resolve_node(key_node, consts)
        if not isinstance(key, str):
            continue
        value = _resolve_node(value_node, consts)
        if value is not _UNRESOLVED:
            out[key] = value
    return out


def _extract_function_calls(
    func_node: ast.FunctionDef, consts: dict[str, Any]
) -> list[dict[str, Any]]:
    """Every ``FunctionCall(function=..., args={...})`` literal reachable from
    ``func_node``, in source order. Reachable-but-not-executed branches (an ``if`` the
    real environment would not take) are included too; this over-approximates ground
    truth rather than under-approximating it, which is the safer default for a
    labeller that only ever asserts a positive match."""
    calls: list[dict[str, Any]] = []
    for node in ast.walk(func_node):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "FunctionCall"
        ):
            continue
        kwargs = {kw.arg: kw.value for kw in node.keywords if kw.arg}
        function_value = _resolve_node(kwargs.get("function"), consts)
        if not isinstance(function_value, str):
            continue
        entry: dict[str, Any] = {
            "function": function_value,
            "args": _dict_literal(kwargs.get("args"), consts),
        }
        placeholder = _dict_literal(kwargs.get("placeholder_args"), consts)
        if placeholder:
            entry["placeholder_args"] = placeholder
        calls.append(entry)
    return calls


def _extract_tasks(path: Path, kind: str) -> dict[str, dict[str, Any]]:
    """``kind`` is ``"user_tasks"`` or ``"injection_tasks"``."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    prefix = "user_task" if kind == "user_tasks" else "injection_task"
    prompt_key = "PROMPT" if kind == "user_tasks" else "GOAL"
    text_key = "prompt" if kind == "user_tasks" else "goal"
    out: dict[str, dict[str, Any]] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        match = _TASK_CLASS_RE.match(node.name)
        if not match:
            continue
        task_id = f"{prefix}_{match.group(2)}"
        consts = _class_body_constants(node)
        text = consts.get(prompt_key, "")
        gt_func = next(
            (s for s in node.body if isinstance(s, ast.FunctionDef) and s.name == "ground_truth"),
            None,
        )
        ground_truth = _extract_function_calls(gt_func, consts) if gt_func is not None else []
        out[task_id] = {
            text_key: text if isinstance(text, str) else "",
            "ground_truth": ground_truth,
        }
    return out


def _extract_tool_names(task_suite_path: Path) -> list[str]:
    tree = ast.parse(task_suite_path.read_text(encoding="utf-8"))
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and any(isinstance(t, ast.Name) and t.id == "TOOLS" for t in node.targets)
            and isinstance(node.value, ast.List)
        ):
            return [elt.id for elt in node.value.elts if isinstance(elt, ast.Name)]
    return []


def _extract_tool_docs(tools_dir: Path, names: set[str]) -> dict[str, str]:
    docs: dict[str, str] = {}
    for path in sorted(tools_dir.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name in names:
                doc = ast.get_docstring(node)
                if doc:
                    first_line = doc.strip().splitlines()[0].strip()
                    docs[node.name] = first_line[:200]
    return docs


def export(agentdojo_root: Path, suites: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    tools_dir = agentdojo_root / "tools"
    for suite in suites:
        suite_dir = agentdojo_root / suite
        tool_names = _extract_tool_names(suite_dir / "task_suite.py")
        tool_docs = _extract_tool_docs(tools_dir, set(tool_names))
        tools = {name: tool_docs.get(name, name) for name in tool_names}
        result[suite] = {
            "tools": tools,
            "user_tasks": _extract_tasks(suite_dir / "user_tasks.py", "user_tasks"),
            "injection_tasks": _extract_tasks(suite_dir / "injection_tasks.py", "injection_tasks"),
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agentdojo-root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--suites", default=",".join(SUITES))
    args = parser.parse_args()

    importable = _try_import_agentdojo()
    print(
        "agentdojo pip-importable: "
        f"{importable} (unused either way; extraction is always the static AST parse below)"
    )

    suites = [s.strip() for s in args.suites.split(",") if s.strip()]
    result = export(args.agentdojo_root, suites)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    n_user = sum(len(v["user_tasks"]) for v in result.values())
    n_injection = sum(len(v["injection_tasks"]) for v in result.values())
    n_tools = sum(len(v["tools"]) for v in result.values())
    print(f"wrote {args.out}")
    print(f"suites={len(result)} user_tasks={n_user} injection_tasks={n_injection} tools={n_tools}")


if __name__ == "__main__":
    main()
