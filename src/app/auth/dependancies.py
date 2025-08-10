from typing import Annotated, Optional

from fastapi import HTTPException, Depends, Header, Cookie

from app.core.db import AsyncDatabase
from app.core.dependancies import get_db
from app.auth.utils import OAuth2PasswordBearerWithCookie
from app.auth.service import UserService, PermissionService


oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="auth/login", refreshUrl="auth/refresh")


def get_refresh_token(
    header_name: Optional[str] = "x_access_token",
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
        if header_token:
            return header_token
        elif cookie_token:
            return cookie_token
        else:
            raise HTTPException(status_code="401", detail="Authentication token missing")

    return _dependency


def get_oauth2_scheme(auth_scheme: OAuth2PasswordBearerWithCookie = Depends(oauth2_scheme)) -> OAuth2PasswordBearerWithCookie:
    return auth_scheme


def get_user_service(db: Annotated[AsyncDatabase, Depends(get_db)]):
    return UserService(db)


def get_token_from_header(token: Annotated[str, Depends(get_oauth2_scheme)]) -> str:
    """Dependency to extract token from Authorization header"""
    return token


def get_permission_service(token: str = Depends(get_token_from_header), user_service: UserService = Depends(get_user_service)):
    return PermissionService(token, user_service)


async def get_current_user(permission_service: str = Depends(get_permission_service)):
    """
    Extract and validate the current user from the access token
    This is how you access token data within routes
    """
    return await permission_service.get_current_user()


def require_role(role: str):
    """
    Extract and validate the current user from the access token
    """

    async def role_checker(permission_service: PermissionService = Depends(get_permission_service)):
        return await permission_service.require_role(role)

    return role_checker


async def require_admin(permission_service: PermissionService = Depends(get_permission_service)):
    return await permission_service.require_role("admin")
