"""Auth-specific response headers.

Authentication responses can contain tokens, session state, or user data and
must never be stored by a browser, proxy, or CDN.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class AuthNoStoreMiddleware(BaseHTTPMiddleware):
    """Add anti-caching headers to every ``/auth`` response."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)

        path = request.url.path
        if path == "/auth" or path.startswith("/auth/"):
            response.headers["Cache-Control"] = "no-store"

        return response
