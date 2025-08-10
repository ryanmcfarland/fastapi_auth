from typing import Optional

from fastapi import HTTPException

from app.core.db import AsyncDatabase
from app.auth.models import RegisterRequest, UserResponse, UserInDB
from app.auth.utils import PasswordUtils, TokenUtils


class UserService:
    def __init__(self, database: AsyncDatabase):
        self.db = database
        self.password_utils = PasswordUtils()
        self.token_utils = TokenUtils()

    async def get_user_by_username(self, username: str) -> Optional[UserInDB]:
        """Get user by username"""
        return await self.db.fetchone("auth.get_user_by_username", {"username": username})

    async def register_user(self, user_data: RegisterRequest) -> UserResponse:
        """Register a new user with proper password hashing."""
        existing_user = await self.get_user_by_username(user_data.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="Username or email already registered")
        password_hash = self.password_utils.hash_password(user_data.password)
        await self.db.execute("auth.insert_user", {"username": user_data.username, "email": user_data.email, "password_hash": password_hash})
        created_user = await self.get_user_by_username(user_data.username)
        return UserResponse(**created_user)

    async def login_user(self, username: str, password: str) -> dict:
        user = await self.authenticate_user(username, password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        token_data = {"sub": user["username"], "roles": user["user_roles"]}
        refresh_token = self.token_utils.create_refresh_token(data=token_data)
        access_token = self.token_utils.create_access_token(data=token_data)
        await self.db.execute("auth.insert_refresh_token", params={"username": username, "refresh_token": refresh_token})
        return {"access_token": access_token, "refresh_token": refresh_token}

    async def logout_user(self, username: str, refresh_token: str) -> None:
        await self.db.execute("auth.delete_refresh_token", params={"username": username, "refresh_token": refresh_token})
        return

    async def authenticate_user(self, username: str, password: str) -> Optional[UserInDB]:
        """Authenticate user with username/password."""
        user = await self.db.fetchone("auth.get_user_by_username", {"username": username})
        if not user or not self.password_utils.verify_password(password, user["password_hash"]):
            return None
        return user

    async def verify_refresh_token(self, token: str, token_type: str) -> bool:
        payload = self.token_utils.decode_token(token)
        if payload.get("type") != token_type:
            raise HTTPException(status_code=401, detail="Invalid token type")
        verified = await self.db.fetchone("auth.verify_refresh_token", params={"username": payload.get("sub", None), "refresh_token": token})
        if not verified:
            raise HTTPException(status_code=401, detail="Invalid token type")
        return self.token_utils.create_access_token(data=payload)

    async def get_current_user(self, token: str):
        """Extract current user from access token"""
        payload = self.token_utils.decode_token(token)
        username = payload.get("sub", None)
        return await self.db.fetchone("auth.get_user_by_username", {"username": username})


class PermissionService:
    def __init__(self, token: str, userService: UserService):
        self.token = token
        self.user_service = userService

    async def get_current_user(self):
        return await self.user_service.get_current_user(self.token)

    async def require_role(self, role: str):
        """Dependency factory to require specific role"""
        current_user = await self.get_current_user()
        if role not in current_user.get("user_roles", []):
            raise HTTPException(status_code=401, detail=f"Missing required role: {role.value}")
        return current_user
