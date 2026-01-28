from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)

        if response.status_code in [307, 308, 301, 302]:
            logger.info(f"IP: {request.client.host} | Path: {request.url.path}")

        return response


def add_logging_middleware(app):
    app.add_middleware(LoggingMiddleware)