"""Request-ID middleware: echo X-Request-ID in/out, attach to logs."""

from __future__ import annotations

import logging
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


REQUEST_ID_HEADER = "X-Request-ID"
log = logging.getLogger("applica.request")


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        rid = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex[:16]
        request.state.request_id = rid
        try:
            response = await call_next(request)
        except Exception:
            log.exception("rid=%s method=%s path=%s unhandled", rid, request.method, request.url.path)
            raise
        response.headers[REQUEST_ID_HEADER] = rid
        log.info(
            "rid=%s method=%s path=%s status=%s",
            rid, request.method, request.url.path, response.status_code,
        )
        return response
