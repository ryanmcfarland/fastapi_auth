from typing import Annotated

from fastapi import Response, APIRouter, HTTPException, Depends
from fastapi.security import OAuth2PasswordRequestForm

import app.auth.models as models

from app.core.utils import ErrorHandlerRoute
from app.auth.service import UserService
from app.auth.dependancies import get_user_service, get_refresh_token

auth_router = APIRouter(prefix="/auth", tags=["auth"], route_class=ErrorHandlerRoute)


@auth_router.post("/register", status_code=201, response_model=models.UserResponse)
async def register(user_data: models.RegisterRequest, user_service: UserService = Depends(get_user_service)):
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
        response.set_cookie(key="refresh_token", value=tokens["refresh_token"], httponly=True, secure=True, samesite="lax", max_age=1 * 24 * 60 * 60)
        return {"access_token": tokens["access_token"], "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {e.__class__.__name__}")


# TODO (mocked)
@auth_router.post("/logout")
def logout(user_service: UserService = Depends(get_user_service)):
    return {"msg": "Logout endpoint hit (mocked)"}


@auth_router.post("/refresh")
async def refresh(refresh_token_cookie: str = Depends(get_refresh_token()), user_service: UserService = Depends(get_user_service)):
    return await user_service.verify_refresh_token(refresh_token_cookie, "refresh")
