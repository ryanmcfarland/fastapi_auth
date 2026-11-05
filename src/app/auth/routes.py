"""Authentication routes module.

Provides endpoints for user registration, login, logout, token refresh, and password reset.
Handles JWT access token and refresh token management with secure HttpOnly cookie storage.
"""

from typing import Annotated

from fastapi import Response, APIRouter, Depends

import app.auth.models as models

from app.api.routing import BaseErrorHandlerRoute
from app.auth.cookies import clear_session_cookies, set_access_token_cookie, set_session_cookies
from app.auth.service import AuthenticationService
from app.auth.security import OAuth2LoginForm
from app.auth.dependancies import get_current_user, get_optional_user
from app.auth.dependancies import get_authentication_service, get_refresh_token
from app.auth.models import AccessTokenPublic

auth_router = APIRouter(prefix="/auth", tags=["auth"], route_class=BaseErrorHandlerRoute)


@auth_router.post("/register", status_code=201, response_model=models.ResponseUser)
async def register(
    user_data: models.RegisterUser,
    authentication_service: AuthenticationService = Depends(get_authentication_service),
):
    """Register a new user account.

    Args:
        user_data: User registration data (username, email, password).
        authentication_service: Injected authentication service dependency.

    Returns:
        ResponseUser: Created user object without sensitive information.
    """
    return await authentication_service.register_user(user_data)


@auth_router.post("/login", response_model=AccessTokenPublic)
async def login(
    response: Response,
    form_data: Annotated[OAuth2LoginForm, Depends()],
    authentication_service: AuthenticationService = Depends(get_authentication_service),
):
    """Authenticate user credentials and return access token.

    Validates username and password, then generates a JWT access token and
    refresh token. Both tokens are also set as HttpOnly cookies so a browser
    can call the API directly without exposing either token to JavaScript. The
    JSON body still contains the access token for non-browser clients.

    Args:
        response: FastAPI Response object to set cookies.
        form_data: OAuth2 login form with username and password.
        authentication_service: Injected authentication service dependency.

    Returns:
        dict: Token object with `access_token`, `token_type`, `expires_in`
        (access token seconds) and `refresh_expires_in` (refresh token seconds).

    Raises:
        HTTPException: 401 if credentials are invalid, 500 for internal errors.
    """
    tokens = await authentication_service.login_user(form_data.identifier, form_data.password)

    set_session_cookies(response, tokens)

    return AccessTokenPublic(
        access_token=tokens.access_token,
        token_type="bearer",
        expires_in=tokens.expires_in,
        refresh_expires_in=tokens.refresh_expires_in,
    )


@auth_router.post("/logout")
async def logout(
    response: Response,
    refresh_token: str = Depends(get_refresh_token()),
    authentication_service: AuthenticationService = Depends(get_authentication_service),
):
    """Logout user by invalidating refresh token and clearing cookie.

    Revokes the refresh token in the database and removes both session cookies.
    Access token is not invalidated server-side but will eventually expire based
    on its TTL.

    Args:
        response: FastAPI Response object to delete cookies.
        refresh_token: Refresh token extracted from cookies via dependency.
        authentication_service: Injected authentication service dependency.

    Returns:
        Response: Empty response with 204 No Content status.

    Raises:
        HTTPException: 401 if refresh token is invalid or missing.
    """
    await authentication_service.logout_user(refresh_token)
    clear_session_cookies(response)
    response.status_code = 204
    return response


@auth_router.post("/refresh", response_model=AccessTokenPublic)
async def refresh(
    response: Response,
    refresh_token_cookie: str = Depends(get_refresh_token()),
    authentication_service: AuthenticationService = Depends(get_authentication_service),
):
    """Refresh access token using valid refresh token.

    Validates the refresh token and generates a new access token. The refresh
    token is reused rather than rotated, so only the access token cookie is
    rewritten. The JSON body still contains the access token for non-browser
    clients.

    Args:
        response: FastAPI Response object to set cookies.
        refresh_token_cookie: Refresh token extracted from cookies via dependency.
        authentication_service: Injected authentication service dependency.

    Returns:
        dict: Token object with a new `access_token`, `token_type`, `expires_in`
        and the refresh token's remaining lifetime as `refresh_expires_in`.

    Raises:
        InvalidTokenError: 401 if refresh token is invalid, expired, or revoked.
    """

    tokens = await authentication_service.refresh_access_token(refresh_token_cookie)

    set_access_token_cookie(response, tokens)

    return AccessTokenPublic(
        access_token=tokens.access_token,
        token_type="bearer",
        expires_in=tokens.expires_in,
        refresh_expires_in=tokens.refresh_expires_in,
    )


@auth_router.get("/me", response_model=models.ResponseUser | None)
def me(current_user=Depends(get_optional_user)):
    """
    Returns current user if authenticated, None if not.
    Useful for clients to check auth state without risking a 401.
    """
    return current_user


@auth_router.get("/profile", response_model=models.ResponseUser)
def profile(current_user=Depends(get_current_user)):
    """Get the current authenticated user's profile.

    Requires valid access token in Authorization header (Bearer scheme).
    Returns the full user profile without sensitive information.

    Args:
        current_user: Current authenticated user extracted from JWT token.

    Returns:
        ResponseUser: User profile object without sensitive information.

    Raises:
        HTTPException: 401 if no valid access token is provided.
    """
    return current_user
