"""``POST /v1/classify`` and ``POST /v1/classify/batch``.

Both routes go through :class:`~forecheck.inference.classifier.Classifier` so
calibration is always applied identically to single and batched requests. When
``backend.capabilities.supports_batching`` is true, the batch route always scores
through :class:`~forecheck.api.batching.MicroBatcher` for real backend-level batching,
then applies calibration and abstention via ``Classifier.classify_from_raw`` — whether
or not a calibration bundle is loaded. Backends that do not support batching fall back
to per-item ``Classifier.classify`` calls, run concurrently in the thread pool.
"""

from __future__ import annotations

import asyncio
import time
from typing import TYPE_CHECKING, Annotated

import anyio
import structlog
from fastapi import APIRouter, Depends

from forecheck.api import audit, metrics
from forecheck.api.auth import Principal
from forecheck.api.deps import (
    AppState,
    get_app_state,
    get_classifier,
    get_settings,
    require_principal,
)
from forecheck.api.settings import Settings
from forecheck.contracts import (
    AbstentionReason,
    BatchClassifyRequest,
    BatchClassifyResponse,
    CalibrationInfo,
    CalibrationMethod,
    ClassifyRequest,
    ClassifyResponse,
    ErrorCode,
    ForecheckError,
)
from forecheck.inference import Classifier

if TYPE_CHECKING:
    from forecheck.contracts import ModelInfo

__all__ = ["router"]

logger = structlog.get_logger("forecheck.routes.classify")

router = APIRouter(tags=["classify"])


def _resolve_timeout_ms(requested_ms: int | None, settings: Settings) -> int:
    if requested_ms is None:
        return settings.request_timeout_ms
    return min(requested_ms, settings.request_timeout_ms)


def _record_classify_metrics(response: ClassifyResponse) -> None:
    for score in response.scores:
        if score.probability is not None:
            metrics.DIMENSION_PROBABILITY.labels(dimension=score.dimension.value).observe(
                score.probability
            )
    for reason in response.abstention_reasons:
        metrics.ABSTENTIONS_TOTAL.labels(reason=reason.value).inc()


def _emit_classify_audit(
    *, item: ClassifyRequest, response: ClassifyResponse, tenant_id: str | None, settings: Settings
) -> None:
    event = audit.build_classify_event(
        request_id=response.request_id,
        tenant_id=tenant_id,
        context=item.context,
        response=response,
        include_raw=item.options.include_uncalibrated,
    )
    audit.emit(event)
    if settings.store_request_bodies:
        audit.store_event(settings.store_request_bodies_path, response.request_id, event)


async def _classify_with_timeout(
    item: ClassifyRequest, classifier: Classifier, settings: Settings
) -> ClassifyResponse:
    timeout_s = _resolve_timeout_ms(item.options.timeout_ms, settings) / 1000.0
    try:
        with anyio.fail_after(timeout_s):
            return await anyio.to_thread.run_sync(classifier.classify, item, abandon_on_cancel=True)
    except TimeoutError as exc:
        raise ForecheckError(ErrorCode.BACKEND_TIMEOUT, "backend timed out") from exc


@router.post("/v1/classify", response_model=ClassifyResponse)
async def classify(
    payload: ClassifyRequest,
    principal: Annotated[Principal, Depends(require_principal)],
    classifier: Annotated[Classifier, Depends(get_classifier)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ClassifyResponse:
    """Score one proposed action against the requested risk dimensions."""
    response = await _classify_with_timeout(payload, classifier, settings)
    _record_classify_metrics(response)
    _emit_classify_audit(
        item=payload, response=response, tenant_id=principal.tenant_id, settings=settings
    )
    return response


def _placeholder_response(
    item: ClassifyRequest, model_info: ModelInfo, *, reason: AbstentionReason
) -> ClassifyResponse:
    """A response used to isolate one batch item's failure from its batch-mates.

    Carries no scores -- ``BatchClassifyResponse.items`` has no per-item error slot in
    the wire contract, so a failed item is represented as a fully abstained response
    rather than failing the whole batch.
    """
    return ClassifyResponse(
        request_id=item.request_id,
        scores=[],
        model=model_info,
        calibration=CalibrationInfo(method=CalibrationMethod.NONE),
        abstained=True,
        abstention_reasons=[reason],
        latency_ms=0.0,
    )


async def _classify_batch_item(item: ClassifyRequest, state: AppState) -> ClassifyResponse:
    """Score and classify one batch item, isolating its failure from its batch-mates."""
    settings = state.settings
    timeout_s = _resolve_timeout_ms(item.options.timeout_ms, settings) / 1000.0
    start = time.perf_counter()
    try:
        with anyio.fail_after(timeout_s):
            if state.batcher is not None:
                raw = await state.batcher.score(item.context, item.options.dimensions)
                return await anyio.to_thread.run_sync(
                    state.classifier.classify_from_raw, item, raw, start, abandon_on_cancel=True
                )
            return await anyio.to_thread.run_sync(
                state.classifier.classify, item, abandon_on_cancel=True
            )
    except TimeoutError:
        logger.warning("classify_batch_item_timeout", request_id=item.request_id)
        return _placeholder_response(
            item, state.backend.model_info, reason=AbstentionReason.BACKEND_TIMEOUT
        )
    except Exception as exc:
        logger.error("classify_batch_item_failed", request_id=item.request_id, error=repr(exc))
        return _placeholder_response(
            item, state.backend.model_info, reason=AbstentionReason.ITEM_FAILED
        )


@router.post("/v1/classify/batch", response_model=BatchClassifyResponse)
async def classify_batch(
    payload: BatchClassifyRequest,
    principal: Annotated[Principal, Depends(require_principal)],
    state: Annotated[AppState, Depends(get_app_state)],
) -> BatchClassifyResponse:
    """Score a batch of proposed actions. One failing item never fails the batch."""
    responses = await asyncio.gather(*(_classify_batch_item(item, state) for item in payload.items))
    for item, response in zip(payload.items, responses, strict=True):
        _record_classify_metrics(response)
        _emit_classify_audit(
            item=item, response=response, tenant_id=principal.tenant_id, settings=state.settings
        )
    return BatchClassifyResponse(items=list(responses))
