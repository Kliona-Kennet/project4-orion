import logging
import sys
import time
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

_LOG_FORMAT = "[%(asctime)s] %(levelname)s %(name)s: %(message)s"

def setup_logging(level: int = logging.INFO) -> None:
    """
    Configure root logger to console at INFO.
    Safe to call multiple times.
    """
    root = logging.getLogger()
    if root.handlers:
        root.setLevel(level)
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))
    root.setLevel(level)
    root.addHandler(handler)

    logging.getLogger("uvicorn").setLevel(level)
    logging.getLogger("uvicorn.error").setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(level)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """
    Logs one line per request with:
      method, path, status, latency_ms, response_size_bytes, request_id
    Also injects X-Request-ID if missing.
    """
    def __init__(self, app: ASGIApp, logger_name: str = "request"):
        super().__init__(app)
        self.logger = logging.getLogger(logger_name)

    async def dispatch(self, request: Request, call_next: Callable):
        start = time.perf_counter()
       
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id

        response: Response = await call_next(request)

        response.headers["X-Request-ID"] = request_id

        latency_ms = (time.perf_counter() - start) * 1000.0
        status = response.status_code
        size_hdr = response.headers.get("content-length")
        try:
            response_size = int(size_hdr) if size_hdr is not None else 0
        except ValueError:
            response_size = 0

        self.logger.info(
            "method=%s path=%s status=%s latency_ms=%.2f response_size_bytes=%d request_id=%s",
            request.method,
            request.url.path,
            status,
            latency_ms,
            response_size,
            request_id,
        )

        return response
