from typing import Optional

from fastapi import HTTPException

from app.core.db import AsyncDatabase
from app.auth.repositories import AuthRepository
from app.auth.utils import PasswordUtils, TokenUtils

import app.auth.models as models


class UserService:
    def __init__(self, database: AsyncDatabase):
        self.user_repo = AuthRepository(database)
        self.password_utils = PasswordUtils()
        self.token_utils = TokenUtils()

    async def register_user(self, user_data: models.RegisterRequest) -> models.UserResponse:
        """Register a new user with proper password hashing."""
        existing_user = await self.user_repo.get_user_by_username(user_data.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username or email already registered")
        password_hash = self.password_utils.hash_password(user_data.password)
        await self.user_repo.insert_user(user_data.username, user_data.email, password_hash)
        created_user = await self.user_repo.get_user_by_username(user_data.username)
        return models.UserResponse(**created_user)

    async def login_user(self, username: str, password: str) -> dict:
        user = await self.authenticate_user(username, password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token_data = {"sub": user["username"], "roles": user["user_roles"]}
        refresh_token = self.token_utils.create_refresh_token(data=token_data)
        access_token = self.token_utils.create_access_token(data=token_data)
        await self.user_repo.insert_refresh_token(username, refresh_token)
        return {"access_token": access_token, "refresh_token": refresh_token}

    async def authenticate_user(self, username: str, password: str) -> Optional[dict]:
        """Authenticate user with username/password."""
        user = await self.user_repo.get_user_by_username(username)
        if not user or not self.password_utils.verify_password(password, user.get("password_hash", "")):
            return None
        return user

    async def logout_user(self, token: str) -> None:
        """ """
        payload = self.token_utils.decode_token(token)
        await self.user_repo.logout_user(payload.get("sub", ""))

    async def verify_refresh_token(self, token: str) -> str:
        payload = self.token_utils.decode_token(token)
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid token type")
        verified: bool = await self.user_repo.verify_refresh_token(payload.get("sub", ""), token)
        if not verified:
            raise HTTPException(status_code=401, detail="Invalid token")
        return self.token_utils.create_access_token(data=payload)

    async def get_current_user(self, token: str) -> models.User:
        """Extract current user from access token"""
        payload = self.token_utils.decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Invalid token type")
        user = await self.user_repo.get_user_by_username(payload.get("sub", ""))
        return models.User(**user)


class PermissionService:
    def __init__(self, token: str, userService: UserService):
        self.token = token
        self.user_service = userService

    async def get_current_user(self) -> models.User:
        return await self.user_service.get_current_user(self.token)

    async def require_role(self, role: str) -> models.User:
        """Dependency factory to require specific role"""
        current_user = await self.get_current_user()
        if role not in current_user.user_roles:
            raise HTTPException(status_code=401, detail=f"Missing required role: {role.value}")
        return current_user

    async def logout_user(self) -> None:
        """You need to be authenitcated to logout. This assures thay"""
        user: models.User = await self.get_current_user()
        await self.user_service.logout_user(user.id)
