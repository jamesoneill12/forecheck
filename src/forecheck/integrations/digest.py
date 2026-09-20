"""Canonical JSON argument digest.

This is the TOCTOU binding primitive described in ``docs/threat-model.md`` (TM-12): the
middleware classifies a set of arguments, then executes only if
``argument_digest(args_to_execute) == classified_digest``. Two mappings that differ only
in key order must digest identically; any value difference must digest differently.
"""

from __future__ import annotations

import base64
import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from datetime import date, datetime, time
from typing import Any

__all__ = ["argument_digest", "canonical_json"]


def _normalise(value: Any) -> Any:
    if value is None or isinstance(value, bool | str | int):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError(f"cannot digest a non-finite float: {value!r}")
        return value
    if isinstance(value, bytes | bytearray):
        return {"__bytes_b64__": base64.b64encode(bytes(value)).decode("ascii")}
    if isinstance(value, datetime | date | time):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(k): _normalise(v) for k, v in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str | bytes | bytearray):
        return [_normalise(v) for v in value]
    if isinstance(value, frozenset | set):
        return sorted(_normalise(v) for v in value)
    raise TypeError(f"cannot digest value of type {type(value).__name__}")


def canonical_json(arguments: Mapping[str, Any]) -> str:
    """Render ``arguments`` as canonical JSON: sorted keys, no whitespace.

    Bytes are base64-normalised, datetimes become ISO-8601 strings, and NaN/Infinity
    floats are rejected outright rather than silently serialised as non-standard JSON.
    """
    normalised = _normalise(dict(arguments))
    return json.dumps(normalised, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def argument_digest(arguments: Mapping[str, Any]) -> str:
    """Sha256 hex digest of the canonical JSON form of ``arguments``."""
    payload = canonical_json(arguments).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
