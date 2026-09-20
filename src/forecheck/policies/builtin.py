"""Accessors for the three policy bundles forecheck ships out of the box.

The canonical YAML files live at the repository's top-level ``policies/`` directory
(see ``policies/README.md`` for what each one is for), sitting alongside ``src/``
rather than inside the installed package. This module first looks for that directory
relative to its own file, which works from a source checkout or an editable install.
A built wheel does not have that directory, so ``pyproject.toml`` force-includes
``policies/`` into the package as ``forecheck/_bundles``; the fallback below reads it
from there via ``importlib.resources``.
"""

from __future__ import annotations

from functools import cache
from importlib import resources
from pathlib import Path

from forecheck.policies.engine import DeterministicPolicyEngine
from forecheck.policies.loader import load_policy_engine

__all__ = [
    "available_bundle_names",
    "builtin_bundle_path",
    "load_builtin_engine",
]

_BUNDLE_FILENAMES: dict[str, str] = {
    "conservative": "conservative.yaml",
    "balanced": "balanced.yaml",
    "permissive": "permissive.yaml",
}


def _policies_root() -> Path:
    here = Path(__file__).resolve()
    for candidate in (here, *here.parents):
        probe = candidate / "policies"
        if probe.is_dir() and (probe / "conservative.yaml").is_file():
            return probe
    packaged = resources.files("forecheck") / "_bundles"
    if packaged.is_dir() and (packaged / "conservative.yaml").is_file():
        return Path(str(packaged))
    raise FileNotFoundError(
        f"could not locate a 'policies/' directory containing the built-in bundles above {here}, "
        "nor a packaged 'forecheck/_bundles' directory"
    )


def available_bundle_names() -> tuple[str, ...]:
    return tuple(sorted(_BUNDLE_FILENAMES))


def builtin_bundle_path(name: str) -> Path:
    try:
        filename = _BUNDLE_FILENAMES[name]
    except KeyError as exc:
        raise KeyError(
            f"unknown built-in policy bundle {name!r}, expected one of {available_bundle_names()}"
        ) from exc
    return _policies_root() / filename


@cache
def load_builtin_engine(name: str) -> DeterministicPolicyEngine:
    return load_policy_engine(builtin_bundle_path(name))
