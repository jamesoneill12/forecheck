"""Version constants that appear in API responses and dataset records."""

from __future__ import annotations

from typing import Final

__version__: Final[str] = "0.1.0"

API_SCHEMA_VERSION: Final[str] = "1.0"
LABEL_DERIVATION_VERSION: Final[str] = "1.0.0"
PROMPT_CONTRACT_VERSION: Final[str] = "1.2.0"
POLICY_DSL_VERSION: Final[str] = "1.0"

__all__ = [
    "API_SCHEMA_VERSION",
    "LABEL_DERIVATION_VERSION",
    "POLICY_DSL_VERSION",
    "PROMPT_CONTRACT_VERSION",
    "__version__",
]
