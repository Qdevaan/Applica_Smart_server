"""RFC 7807 problem-details error contract."""

from __future__ import annotations

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def _problem(status: int, title: str, detail: str | None = None, type_: str = "about:blank", **extra) -> dict:
    body = {"type": type_, "title": title, "status": status}
    if detail:
        body["detail"] = detail
    body.update(extra)
    return body


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=_problem(exc.status_code, exc.__class__.__name__, str(exc.detail)),
        media_type="application/problem+json",
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=_problem(
            422,
            "Validation Error",
            "Request payload failed schema validation.",
            errors=exc.errors(),
        ),
        media_type="application/problem+json",
    )


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=_problem(500, "Internal Server Error", str(exc) or exc.__class__.__name__),
        media_type="application/problem+json",
    )
