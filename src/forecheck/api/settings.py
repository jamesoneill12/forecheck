"""Service configuration, read from ``FORECHECK_*`` environment variables.

Field names here are fixed by ``.env.example`` and must not drift from it. The one
exception is ``otel_exporter_otlp_endpoint``, which reads the unprefixed
``OTEL_EXPORTER_OTLP_ENDPOINT`` because that variable name is an OpenTelemetry SDK
convention, not a forecheck one.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from forecheck.contracts import Limits

__all__ = ["Settings"]

BackendName = Literal["mock", "hf", "rule_baseline"]
AuthMode = Literal["none", "static_token", "header_passthrough"]

_BUILTIN_BUNDLE_NAMES: tuple[str, ...] = ("conservative", "balanced", "permissive")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="FORECHECK_", env_file=".env", extra="ignore", case_sensitive=False
    )

    backend: BackendName = "mock"
    model_id: str | None = None
    adapter_id: str | None = None
    calibration_path: Path | None = None
    policy_bundle: str = "conservative"
    policy_bundle_allowlist: str = ",".join(_BUILTIN_BUNDLE_NAMES)
    device: str = "auto"
    host: str = "0.0.0.0"  # noqa: S104
    port: int = 8000
    request_timeout_ms: int = 5000
    max_batch: int = 16
    max_batch_wait_ms: int = 10
    log_level: str = "info"
    store_request_bodies: bool = False
    store_request_bodies_path: Path = Path("./forecheck-stored-bodies")
    feedback_sink_path: Path = Path("./forecheck-feedback")
    auth_mode: AuthMode = "none"
    static_token: str | None = None
    auth_header_name: str = "X-Forecheck-Principal"
    tenant_header_name: str = "X-Forecheck-Tenant-Id"
    policy_bundle_header_name: str = "X-Forecheck-Policy-Bundle"
    otel_enabled: bool = False
    otel_exporter_otlp_endpoint: str | None = Field(
        default=None, validation_alias="OTEL_EXPORTER_OTLP_ENDPOINT"
    )
    max_request_bytes: int = Limits.MAX_REQUEST_BYTES
    thread_pool_workers: int = 8

    def allowlisted_bundles(self) -> tuple[str, ...]:
        names = {n.strip() for n in self.policy_bundle_allowlist.split(",") if n.strip()}
        names.add(self.policy_bundle)
        return tuple(sorted(names))
