import logging
import time

from starlette.middleware.base import BaseHTTPMiddleware

from config import get_settings

log = logging.getLogger("api.middleware")

settings = get_settings()


# Documnentation: https://www.starlette.io/middleware/#basehttpmiddleware
# https://medium.com/@grigdave/advanced-custom-exception-handling-in-fastapi-middleware-7ce4c8405267
class LoggingMiddleware(BaseHTTPMiddleware):
    """Simple middleware to log incoming requests and add process time to header"""

    async def dispatch(self, request, call_next):
        start_time = time.perf_counter()
        try:
            response = await call_next(request)
            process_time = time.perf_counter() - start_time
            log.info(f"{request.method.upper()} {request.url.path} : {response.status_code} : {process_time:.2f} ms")
            response.headers["X-Process-Time"] = str(process_time)
            return response
        except Exception as e:
            process_time = time.perf_counter() - start_time
            log.error(f"{request.method.upper()} {request.url.path} : {type(e).__name__} : {process_time:.2f} ms", exc_info=True)
            raise
