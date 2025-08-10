import logging
import time

from typing import Callable

from fastapi import Request, Response
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware

log = logging.getLogger("core.utils")


# Documnentation: https://www.starlette.io/middleware/#basehttpmiddleware


class LoggingMiddleware(BaseHTTPMiddleware):
    """Simple middleware to log incoming requests and add process time to header"""

    async def dispatch(self, request, call_next):
        start_time = time.perf_counter()
        response = await call_next(request)
        process_time = time.perf_counter() - start_time
        log.info(f"{request.method.upper()} {request.url.path} : {response.status_code} : {process_time:.2f} ms")
        response.headers["X-Process-Time"] = str(process_time)
        return response


class ErrorHandlerRoute(APIRoute):
    """
    Custom APIRoute that logs errors for all routes
    """

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            try:
                response = await original_route_handler(request)
                return response
            except Exception as e:
                log.error(f"{request.method} : {self.path} - Request Exception : {type(e).__name__}")
                raise

        return custom_route_handler
