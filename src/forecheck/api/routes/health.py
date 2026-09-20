"""Liveness, readiness and version endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from forecheck.api.deps import AppState, get_app_state
from forecheck.contracts import LABEL_SCHEMA_VERSION, SCHEMA_VERSION, ErrorCode, ForecheckError
from forecheck.inference.prompt import prompt_contract_hash
from forecheck.version import __version__

__all__ = ["router"]

router = APIRouter(tags=["health"])


class LiveResponse(BaseModel):
    status: str = "live"


class ReadyResponse(BaseModel):
    status: str = "ready"


class PolicyBundleRef(BaseModel):
    bundle_id: str
    bundle_hash: str


class VersionResponse(BaseModel):
    forecheck_version: str
    schema_version: str
    label_schema_version: str
    prompt_contract_hash: str
    backend: str
    model_id: str
    calibration_artifact_id: str | None
    policy_bundles: list[PolicyBundleRef]
    device: str
    torch_available: bool


@router.get("/health/live")
async def live() -> LiveResponse:
    """Always 200 once the process has started; does not depend on backend state."""
    return LiveResponse()


@router.get("/health/ready")
async def ready(state: Annotated[AppState, Depends(get_app_state)]) -> ReadyResponse:
    """503 until the backend, calibration and policy bundles have loaded and warmed up."""
    if not state.ready:
        raise ForecheckError(ErrorCode.MODEL_NOT_READY, "backend is not ready")
    return ReadyResponse()


@router.get("/version")
async def version(state: Annotated[AppState, Depends(get_app_state)]) -> VersionResponse:
    """Everything needed to reproduce a decision: versions, hashes and loaded bundles."""
    model_info = state.backend.model_info
    return VersionResponse(
        forecheck_version=__version__,
        schema_version=SCHEMA_VERSION,
        label_schema_version=LABEL_SCHEMA_VERSION,
        prompt_contract_hash=prompt_contract_hash(),
        backend=model_info.backend,
        model_id=model_info.model_id,
        calibration_artifact_id=(
            state.calibration_bundle.artifact_id if state.calibration_bundle is not None else None
        ),
        policy_bundles=[
            PolicyBundleRef(bundle_id=engine.bundle_id, bundle_hash=engine.bundle_hash)
            for engine in state.policy_engines.values()
        ],
        device=state.device.kind,
        torch_available=state.device.torch_available,
    )
