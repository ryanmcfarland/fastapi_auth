from typing import Annotated

from fastapi import Response, APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm

from config import get_settings

import app.auth.models as models

from app.core.utils import ErrorHandlerRoute
from app.auth.service import UserService
from app.auth.dependancies import get_user_service, get_refresh_token, get_permission_service

settings = get_settings()

auth_router = APIRouter(prefix="/auth", tags=["auth"], route_class=ErrorHandlerRoute)


@auth_router.post("/register", status_code=201, response_model=models.UserResponse)
async def register(user_data: models.RegisterRequest, user_service: UserService = Depends(get_user_service)):
    """ """
    try:
        return await user_service.register_user(user_data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@auth_router.post("/login", response_model=models.Token)
async def login(response: Response, form_data: Annotated[OAuth2PasswordRequestForm, Depends()], user_service: UserService = Depends(get_user_service)):
    try:
        tokens = await user_service.login_user(form_data.username, form_data.password)
        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh_token"],
            httponly=settings.HTTP_ONLY,
            secure=settings.SECURE_COOKIES,
            samesite="lax",
            max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        )
        return {"access_token": tokens["access_token"], "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {e.__class__.__name__}")


@auth_router.post("/logout")
async def logout(response: Response, refresh_token: str = Depends(get_refresh_token()), user_service: UserService = Depends(get_user_service)):
    """ """
    await user_service.logout_user(refresh_token)
    response.delete_cookie(key="refresh_token")
    response.status_code = 204
    return response


@auth_router.post("/refresh", response_model=models.Token)
async def refresh(refresh_token_cookie: str = Depends(get_refresh_token()), user_service: UserService = Depends(get_user_service)):
    token = await user_service.verify_refresh_token(refresh_token_cookie)
    return {"access_token": token, "token_type": "bearer"}
