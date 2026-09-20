"""Digest-not-value redaction utilities shared by audit logging and body storage."""

from __future__ import annotations

import hashlib
import json
from typing import Any

__all__ = ["REDACTED", "digest_json", "digest_text", "redact_mapping"]

REDACTED = "[redacted]"


def digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def digest_json(value: object) -> str:
    canonical = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return digest_text(canonical)


def redact_mapping(mapping: dict[str, Any]) -> dict[str, str]:
    """Replace every value with a fixed sentinel, keeping only the key shape.

    Used when a caller needs to know *that* a field was present without ever seeing
    its content, e.g. when persisting a request body for later inspection.
    """
    return dict.fromkeys(mapping, REDACTED)
