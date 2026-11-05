from typing import Annotated, Optional

from fastapi import HTTPException, Depends, Header, Cookie

from app.core.db import AsyncDatabase

from app.core.dependancies import get_db
from app.auth.security import OAuth2PasswordBearerWithCookie
from app.auth.service import CoreUserService, AuthenticationService, AuthorizationService
from app.auth import models

# Note (asof 2025-08-16) refreshUrl parameter is not used
oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="auth/login", refreshUrl="auth/refresh")
oauth2_scheme_optional = OAuth2PasswordBearerWithCookie(tokenUrl="auth/login", refreshUrl="auth/refresh", auto_error=False)


def get_refresh_token(
    header_name: Optional[str] = "x-refresh-token",
    cookie_name: Optional[str] = "refresh_token",
):
    """
    Returns a FastAPI dependency that extracts a token from either a custom header or cookie.

    Header name and cookie name are optional -> can be used for other tokens / sessions.
    """

    def _dependency(
        header_token: Optional[str] = Header(None, alias=header_name, include_in_schema=False),
        cookie_token: Optional[str] = Cookie(None, alias=cookie_name),
    ) -> str:
        """Resolve a token, preferring the current header over legacy header/cookie."""
        # Prefer the header form, then the legacy underscore form, then cookie.
        if header_token:
            return header_token
        elif cookie_token:
            return cookie_token
        else:
            raise HTTPException(status_code=401, detail="Authentication token missing")

    return _dependency


def get_oauth2_scheme(auth_scheme: OAuth2PasswordBearerWithCookie = Depends(oauth2_scheme)) -> OAuth2PasswordBearerWithCookie:
    return auth_scheme


def get_user_service(
    db: Annotated[AsyncDatabase, Depends(get_db)],
) -> CoreUserService:
    return CoreUserService(db)


def get_authentication_service(
    db: Annotated[AsyncDatabase, Depends(get_db)],
) -> AuthenticationService:
    return AuthenticationService(db)


def get_authorization_service(
    db: Annotated[AsyncDatabase, Depends(get_db)],
) -> AuthorizationService:
    return AuthorizationService(db)


def get_token_from_header(
    token: Annotated[str, Depends(get_oauth2_scheme)],
) -> str:
    """Dependency to extract token from Authorization header"""
    return token


def get_optional_token_from_header(
    token: Annotated[str | None, Depends(oauth2_scheme_optional)],
) -> str | None:
    """Dependency to extract token from Authorization header, but return None if no token is provided"""
    return token


async def get_current_user(
    token: str = Depends(get_token_from_header),
    user_service: CoreUserService = Depends(get_user_service),
) -> models.User:
    """
    Extract and validate the current user from the access token
    This is how you access token data within routes
    """
    return await user_service.get_current_user(token)


async def get_optional_user(
    token: str | None = Depends(oauth2_scheme_optional),
    user_service: CoreUserService = Depends(get_user_service),
) -> models.User | None:
    """Extract and validate the current user from the access token, but return None if no token is provided"""
    if token is None:
        return None
    try:
        return await user_service.get_current_user(token)
    except Exception:
        return None


def require_role(role: str):
    """Factory function to create a dependency that checks if the current user has a specific role.

    Usage: Depends(require_role("admin")) to require admin role for a route.
    """

    async def role_checker(
        authorization_service: AuthorizationService = Depends(get_authorization_service),
        current_user: models.User = Depends(get_current_user),
    ) -> models.User:
        return await authorization_service.require_role(current_user, role)

    return role_checker


def require_admin(admin_user=Depends(require_role("admin"))) -> models.User:
    """Dependency to require admin role for a route"""
    return admin_user
