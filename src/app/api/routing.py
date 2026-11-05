import logging

from typing import Callable

from fastapi import Request, Response, HTTPException
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from app.core.exceptions import CustomValidationError, DBOperationError, ServiceError

log = logging.getLogger("api.routing")


class BaseErrorHandlerRoute(APIRoute):
    """Custom APIRoute that intercepts exceptions and converts them to structured JSON responses.

    Attach to a FastAPI router via `router = APIRouter(route_class=BaseErrorHandlerRoute)`
    to apply consistent error handling across all routes in that router.

    Exception handling priority (first match wins):
        HTTPException          → re-raised as-is for FastAPI's default handler
        RequestValidationError → 422 with field-level detail
        ValidationError        → 422 with field-level detail
        CustomValidationError  → 422 with domain-specific detail
        DBOperationError          → status code and content from the exception
        ServiceError           → status code and content from the exception
        ValueError             → 400 with the exception message
        Exception (catch-all)  → 500 with a generic message

    If handle_exception returns None (which should not happen given the catch-all),
    the route handler falls back to a 500 HTTPException chained to the original exc.
    """

    def get_route_handler(self) -> Callable:
        """Wrap the original route handler with exception interception."""
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            try:
                return await original_route_handler(request)
            except Exception as exc:
                return self.handle_exception(exc, request)

        return custom_route_handler

    def handle_exception(self, exc: Exception, request: Request) -> Response | None:
        """Convert an exception into an appropriate HTTP response.

        Args:
            exc: The exception raised during request handling.
            request: The incoming FastAPI request, used for logging context.

        Returns:
            A JSONResponse with an appropriate status code and body, or None
            if no handler matched (in practice, the catch-all prevents None).

        Raises:
            HTTPException: Re-raises HTTPExceptions directly so FastAPI's own
                exception handlers (e.g. for 404/405) continue to work correctly.
        """
        log.debug("%s : %s -> handling exception : %s", request.method, self.path, exc.__class__.__name__, exc_info=exc)

        # Let FastAPI's built-in HTTPException handler deal with this — suppressing the chain avoids noise in the traceback.
        if isinstance(exc, HTTPException):
            raise exc from None

        # Handle validation errors from FastAPI and Pydantic with detailed field info
        if isinstance(exc, (RequestValidationError, ValidationError)):
            return JSONResponse(
                status_code=422,
                content={
                    "detail": "Validation failed",
                    "errors": {e["loc"][-1]: e["msg"] for e in exc.errors()},
                },
            )
        # Handle custom domain validation errors with their own structure
        if isinstance(exc, CustomValidationError):
            return JSONResponse(status_code=422, content={"detail": str(exc), "errors": exc.errors})
        if isinstance(exc, DBOperationError):
            return JSONResponse(status_code=exc.status_code, content=exc.content)
        if isinstance(exc, ServiceError):
            return JSONResponse(status_code=exc.status_code, content=exc.content)
        if isinstance(exc, ValueError):
            return JSONResponse(status_code=400, content={"detail": str(exc)})
        # Catch-all for any other exceptions — log the details and return a generic 500 response without exposing internal info.
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
