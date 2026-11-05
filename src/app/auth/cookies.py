"""HttpOnly session cookie helpers for authentication responses.

All session cookies must share the same attributes so the browser sends them toboth the API (``/api/*`` through nginx) and the Next.js frontend.
In particular ``path`` must be ``/``: a narrower path would hide the access token from the Next.js middleware and Server Components.
"""

from fastapi import Response

from app.auth.service import LoginTokens, RefreshedTokens
from config import get_settings

settings = get_settings()

COOKIE_PATH = "/"
COOKIE_SAMESITE = "lax"


def _set_session_cookie(response: Response, key: str, value: str, max_age: int) -> None:
    """Set one HttpOnly session cookie with the shared production attributes.

    Args:
        response: FastAPI response that will carry the ``Set-Cookie`` header.
        key: Cookie name.
        value: Cookie value.
        max_age: Lifetime in seconds. Clamped to a positive value so a token
            that is about to expire cannot delete the cookie.
    """
    response.set_cookie(
        key=key,
        value=value,
        httponly=settings.http_only,
        secure=settings.secure_cookies,
        samesite=COOKIE_SAMESITE,
        path=COOKIE_PATH,
        max_age=max(1, int(max_age)),
    )


def set_access_token_cookie(response: Response, tokens: RefreshedTokens) -> None:
    """Expose the access token as an HttpOnly cookie.

    Args:
        response: FastAPI response that will carry the ``Set-Cookie`` header.
        tokens: Token pair containing the new access token and its lifetime.
    """
    _set_session_cookie(response, settings.access_token_cookie_name, tokens.access_token, tokens.expires_in)


def set_refresh_token_cookie(response: Response, tokens: LoginTokens) -> None:
    """Expose the refresh token as an HttpOnly cookie.

    Args:
        response: FastAPI response that will carry the ``Set-Cookie`` header.
        tokens: Token pair containing the new refresh token and its lifetime.
    """
    _set_session_cookie(response, settings.refresh_token_cookie_name, tokens.refresh_token, tokens.refresh_expires_in)


def set_session_cookies(response: Response, tokens: LoginTokens) -> None:
    """Set both the access and refresh token cookies after a successful login.

    Args:
        response: FastAPI response that will carry the ``Set-Cookie`` headers.
        tokens: Newly issued access/refresh token pair.
    """
    set_access_token_cookie(response, tokens)
    set_refresh_token_cookie(response, tokens)


def clear_session_cookies(response: Response) -> None:
    """Expire both session cookies.

    The ``path`` must match the path used when the cookies were created,
    otherwise the browser keeps the original cookies.

    Args:
        response: FastAPI response that will carry the ``Set-Cookie`` headers.
    """
    response.delete_cookie(key=settings.access_token_cookie_name, path=COOKIE_PATH)
    response.delete_cookie(key=settings.refresh_token_cookie_name, path=COOKIE_PATH)
