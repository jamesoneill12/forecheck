"""The forecheck FastAPI service: settings, routes, auth, audit, metrics and OTel.

Nothing here defines a wire type; request/response bodies come from
:mod:`forecheck.contracts`. This package only wires those contracts to HTTP.
"""

from __future__ import annotations

from forecheck.api.app import create_app
from forecheck.api.settings import Settings

__all__ = ["Settings", "create_app"]
