"""One exception handler family rendering every failure into :class:`ErrorResponse`.

Validation error messages never include the offending value, only its dotted
``field_path``: pydantic v2 error messages describe the constraint that failed
(``"String should have at most 512 characters"``), not the input itself, but as
defense in depth this module still discards everything except ``loc`` and never
forwards ``exc.errors()`` verbatim.
"""

from __future__ import annotations

import traceback
from typing import TYPE_CHECKING

import structlog
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from forecheck.contracts import ErrorBody, ErrorCode, ErrorResponse, ForecheckError
from forecheck.contracts.errors import HTTP_STATUS_FOR_CODE

if TYPE_CHECKING:
    from fastapi import FastAPI
    from starlette.requests import Request

__all__ = ["install_exception_handlers"]

logger = structlog.get_logger("forecheck.errors")


def _request_id(request: Request) -> str | None:
    state = getattr(request, "state", None)
    return getattr(state, "request_id", None) if state is not None else None


def _field_path(loc: tuple[int | str, ...]) -> str:
    parts = [str(p) for p in loc if p != "body"]
    return ".".join(parts) if parts else "<body>"


def _json_response(
    request: Request, code: ErrorCode, message: str, field_path: str | None
) -> JSONResponse:
    body = ErrorResponse(
        request_id=_request_id(request),
        error=ForecheckError(code, message, field_path=field_path).to_body(),
    )
    return JSONResponse(
        status_code=HTTP_STATUS_FOR_CODE[code], content=body.model_dump(mode="json")
    )


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(ForecheckError)
    async def _forecheck_error_handler(request: Request, exc: ForecheckError) -> JSONResponse:
        body = ErrorResponse(request_id=_request_id(request), error=exc.to_body())
        return JSONResponse(status_code=exc.http_status, content=body.model_dump(mode="json"))

    @app.exception_handler(RequestValidationError)
    async def _validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        errors = exc.errors()
        first = errors[0] if errors else None
        loc = tuple(first["loc"]) if first is not None else ()
        field_path = _field_path(loc) if loc else None
        if loc and loc[-1] == "schema_version":
            return _json_response(
                request,
                ErrorCode.UNSUPPORTED_SCHEMA_VERSION,
                "unsupported schema_version",
                field_path,
            )
        return _json_response(
            request, ErrorCode.VALIDATION_FAILED, "request validation failed", field_path
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        body = ErrorResponse(
            request_id=_request_id(request),
            error=ErrorBody(
                code=ErrorCode.INTERNAL_ERROR, message=str(exc.detail), retryable=False
            ),
        )
        return JSONResponse(status_code=exc.status_code, content=body.model_dump(mode="json"))

    @app.exception_handler(TimeoutError)
    async def _timeout_handler(request: Request, exc: TimeoutError) -> JSONResponse:
        del exc
        return _json_response(request, ErrorCode.BACKEND_TIMEOUT, "backend timed out", None)

    @app.exception_handler(Exception)
    async def _unexpected_error_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.error(
            "unhandled_exception",
            request_id=_request_id(request),
            error=repr(exc),
            traceback=traceback.format_exc(),
        )
        return _json_response(request, ErrorCode.INTERNAL_ERROR, "internal server error", None)
