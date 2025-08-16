import logging
import time

from functools import lru_cache
from pathlib import Path
from typing import Callable

from fastapi import Request, Response, HTTPException
from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware

from config import get_settings

log = logging.getLogger("core.utils")

settings = get_settings()


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
            except HTTPException as e:
                log.error(f"{request.method} : {self.path} - HTTP Exception : {type(e).__name__} : {e.status_code}")
                raise
            except Exception as e:
                log.error(f"{request.method} : {self.path} - Request Exception : {type(e).__name__}")
                raise

        return custom_route_handler


@lru_cache(maxsize=64)
def load_sql_query(query_name: str, module: str = None, base_path: Path = settings.CODE_DIR) -> str:
    """
    SQL loader with configurable base path parameter

    Usage:
    - Production: load_sql_query("login_user")
    - Tests: load_sql_query("auth", "login_user", "tests/sql_queries")
    """
    if module:
        query_path = base_path / "sql_queries" / module / f"{query_name}.sql"
    else:
        query_path = base_path / "sql_queries" / f"{query_name}.sql"

    try:
        content = query_path.read_text(encoding="utf-8").strip()
        log.debug(f"Loaded SQL query: {module}/{query_name} from {base_path}")
        return content
    except FileNotFoundError:
        raise FileNotFoundError(f"SQL query not found: {query_path}")
    except Exception as e:
        log.error(f"Error loading SQL query {query_path}: {e}")
        raise
