"""Dependency wiring: constructs the backend, classifier, policy engines and auth
provider once at startup, and exposes them to routes via FastAPI ``Depends``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

import anyio
import structlog
from starlette.requests import Request

from forecheck.api.auth import (
    AuthProvider,
    HeaderPassthroughAuth,
    NoAuth,
    Principal,
    StaticTokenAuth,
)
from forecheck.api.batching import MicroBatcher
from forecheck.api.device import DeviceInfo, detect
from forecheck.api.settings import Settings
from forecheck.calibration.store import load_bundle
from forecheck.contracts import (
    ActionContext,
    AgentIdentity,
    ClassifyRequest,
    ErrorCode,
    ForecheckError,
    ProposedAction,
    UserObjective,
)
from forecheck.contracts import (
    Principal as ContextPrincipal,
)
from forecheck.evaluation.baselines import RuleBaselineBackend
from forecheck.inference import Classifier, HFBackend, HFBackendConfig, MockBackend
from forecheck.policies.builtin import available_bundle_names, load_builtin_engine
from forecheck.policies.engine import DeterministicPolicyEngine
from forecheck.policies.loader import load_policy_engine

if TYPE_CHECKING:
    from forecheck.calibration.base import CalibratorBundle
    from forecheck.inference.base import ClassifierBackend

__all__ = [
    "AppState",
    "build_app_state",
    "get_app_state",
    "get_classifier",
    "get_policy_engine",
    "get_settings",
    "require_principal",
    "resolve_policy_bundle_id",
    "run_warmup",
    "shutdown_app_state",
]

logger = structlog.get_logger("forecheck.deps")


@dataclass(slots=True)
class AppState:
    settings: Settings
    backend: ClassifierBackend
    classifier: Classifier
    calibration_bundle: CalibratorBundle | None
    policy_engines: dict[str, DeterministicPolicyEngine]
    auth_provider: AuthProvider
    batcher: MicroBatcher | None
    device: DeviceInfo
    ready: bool = field(default=False)


def _construct_backend(settings: Settings) -> ClassifierBackend:
    if settings.backend == "mock":
        return MockBackend()
    if settings.backend == "hf":
        if not settings.model_id:
            raise ForecheckError(
                ErrorCode.VALIDATION_FAILED,
                "FORECHECK_MODEL_ID is required when FORECHECK_BACKEND=hf",
            )
        device = None if settings.device == "auto" else settings.device
        config = HFBackendConfig(
            model_id=settings.model_id, adapter_id=settings.adapter_id, device=device
        )
        return HFBackend(config)
    if settings.backend == "rule_baseline":
        return RuleBaselineBackend()
    raise ForecheckError(ErrorCode.INTERNAL_ERROR, f"unknown backend {settings.backend!r}")


def _load_policy_engines(settings: Settings) -> dict[str, DeterministicPolicyEngine]:
    engines: dict[str, DeterministicPolicyEngine] = {}
    builtin_names = set(available_bundle_names())
    for name in settings.allowlisted_bundles():
        if name in builtin_names:
            engines[name] = load_builtin_engine(name)
        else:
            engines[name] = load_policy_engine(Path(name))
    return engines


def _construct_auth_provider(settings: Settings) -> AuthProvider:
    if settings.auth_mode == "none":
        return NoAuth()
    if settings.auth_mode == "static_token":
        if not settings.static_token:
            raise ForecheckError(
                ErrorCode.INTERNAL_ERROR,
                "FORECHECK_STATIC_TOKEN is required when FORECHECK_AUTH_MODE=static_token",
            )
        return StaticTokenAuth(
            settings.static_token, tenant_header_name=settings.tenant_header_name
        )
    return HeaderPassthroughAuth(
        settings.auth_header_name, tenant_header_name=settings.tenant_header_name
    )


def _warmup_context() -> ActionContext:
    return ActionContext(
        objective=UserObjective(text="forecheck startup warm-up request."),
        principal=ContextPrincipal(id="forecheck-warmup"),
        agent=AgentIdentity(id="forecheck-warmup"),
        proposed_action=ProposedAction(tool_name="noop"),
    )


async def build_app_state(settings: Settings) -> AppState:
    backend = _construct_backend(settings)
    calibration_bundle = (
        load_bundle(settings.calibration_path) if settings.calibration_path is not None else None
    )
    classifier = Classifier(backend, calibration_bundle)
    policy_engines = _load_policy_engines(settings)
    auth_provider = _construct_auth_provider(settings)
    batcher = (
        MicroBatcher(
            backend, max_batch_size=settings.max_batch, max_wait_ms=settings.max_batch_wait_ms
        )
        if backend.capabilities.supports_batching
        else None
    )
    return AppState(
        settings=settings,
        backend=backend,
        classifier=classifier,
        calibration_bundle=calibration_bundle,
        policy_engines=policy_engines,
        auth_provider=auth_provider,
        batcher=batcher,
        device=detect(),
    )


async def run_warmup(state: AppState) -> None:
    await anyio.to_thread.run_sync(state.backend.warmup)
    warmup_request = ClassifyRequest(context=_warmup_context())
    await anyio.to_thread.run_sync(state.classifier.classify, warmup_request)


async def shutdown_app_state(state: AppState) -> None:
    if state.batcher is not None:
        await state.batcher.aclose()
    await anyio.to_thread.run_sync(state.backend.close)


def get_app_state(request: Request) -> AppState:
    state: AppState = request.app.state.forecheck
    return state


def get_settings(request: Request) -> Settings:
    return get_app_state(request).settings


def get_classifier(request: Request) -> Classifier:
    return get_app_state(request).classifier


def resolve_policy_bundle_id(
    *, header_value: str | None, body_value: str | None, settings: Settings
) -> str:
    requested = header_value or body_value
    if requested is None:
        return settings.policy_bundle
    if requested not in settings.allowlisted_bundles():
        raise ForecheckError(
            ErrorCode.FORBIDDEN, f"policy bundle {requested!r} is not in the allowlist"
        )
    return requested


def get_policy_engine(state: AppState, bundle_id: str) -> DeterministicPolicyEngine:
    engine = state.policy_engines.get(bundle_id)
    if engine is None:
        raise ForecheckError(
            ErrorCode.POLICY_BUNDLE_NOT_FOUND, f"policy bundle {bundle_id!r} is not loaded"
        )
    return engine


def require_principal(request: Request) -> Principal:
    state = get_app_state(request)
    principal = state.auth_provider.authenticate(request)
    request.state.tenant_id = principal.tenant_id
    return principal
