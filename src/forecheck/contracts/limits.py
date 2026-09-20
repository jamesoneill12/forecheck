"""Hard request limits.

These are contract, not configuration: a client that stays inside them gets a stable
error surface, and the server can bound memory before parsing finishes. Serving-side
soft limits (timeouts, batch sizes) live in ``forecheck.api.settings`` instead.
"""

from __future__ import annotations

from typing import Final

__all__ = ["Limits"]


class Limits:
    SHORT_STR: Final[int] = 512
    MEDIUM_STR: Final[int] = 8_192
    LONG_STR: Final[int] = 65_536

    MAX_ROLES: Final[int] = 128
    MAX_ENTITLEMENTS: Final[int] = 512
    MAX_SCOPES: Final[int] = 512
    MAX_TRAJECTORY_STEPS: Final[int] = 64
    MAX_OBSERVATIONS: Final[int] = 64
    MAX_RESOURCES: Final[int] = 64
    MAX_POLICIES: Final[int] = 64

    MAX_REQUEST_BYTES: Final[int] = 1_048_576
    MAX_BATCH_ITEMS: Final[int] = 32

    MAX_PROMPT_TOKENS: Final[int] = 8_192
