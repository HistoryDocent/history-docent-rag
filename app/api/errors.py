from __future__ import annotations

from typing import Any

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiErrorModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ApiValidationIssue(ApiErrorModel):
    field: str = Field(min_length=1)
    message: str = Field(min_length=1)
    error_type: str = Field(min_length=1)


class ApiErrorDetail(ApiErrorModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    details: tuple[ApiValidationIssue, ...] = Field(default_factory=tuple)


class ApiErrorResponse(ApiErrorModel):
    error: ApiErrorDetail


def install_exception_handlers(app) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return _json_error(
            status_code=422,
            code="validation_error",
            message="Request validation failed.",
            details=_validation_issues(exc),
        )

    @app.exception_handler(HTTPException)
    async def fastapi_http_exception_handler(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        return _http_error_response(exc)

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        return _http_error_response(exc)

    @app.exception_handler(Exception)
    async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        return _json_error(
            status_code=500,
            code="internal_error",
            message="Internal server error.",
        )


def _http_error_response(exc: HTTPException | StarletteHTTPException) -> JSONResponse:
    code = "http_error"
    message = "Request failed."
    if isinstance(exc.detail, dict):
        code = _safe_error_code(exc.detail.get("code")) or code
        message = _safe_error_message(exc.detail.get("message")) or message
    elif isinstance(exc.detail, str):
        message = _safe_error_message(exc.detail) or message
    return _json_error(status_code=exc.status_code, code=code, message=message)


def _json_error(
    *,
    status_code: int,
    code: str,
    message: str,
    details: tuple[ApiValidationIssue, ...] = (),
) -> JSONResponse:
    body = ApiErrorResponse(
        error=ApiErrorDetail(code=code, message=message, details=details)
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json"),
    )


def _validation_issues(exc: RequestValidationError) -> tuple[ApiValidationIssue, ...]:
    issues: list[ApiValidationIssue] = []
    for error in exc.errors():
        issues.append(
            ApiValidationIssue(
                field=_format_validation_location(
                    error.get("loc", ()),
                    message=str(error.get("msg", "")),
                ),
                message=str(error.get("msg", "Invalid value.")),
                error_type=str(error.get("type", "value_error")),
            )
        )
    return tuple(issues)


def _format_validation_location(location: Any, *, message: str) -> str:
    if not isinstance(location, tuple | list):
        return "request"
    parts = [str(part) for part in location if part not in {"body", "query", "path"}]
    if parts:
        return ".".join(parts)
    lowered = message.lower()
    for field_name in ("query", "request_id", "place_context", "provider_mode"):
        if field_name in lowered:
            return field_name
    return "request"


def _safe_error_code(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped or len(stripped) > 80:
        return None
    return stripped


def _safe_error_message(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    if not stripped or len(stripped) > 200:
        return None
    return stripped
