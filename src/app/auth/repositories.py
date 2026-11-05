# pyright: reportArgumentType=false
# pyright: reportReturnType=false

from datetime import datetime
from typing import TypedDict

from app.core.db import AsyncDatabase
from app.core.utils import load_sql_query


class UserDict(TypedDict):
    id: int
    username: str
    display_name: str
    email: str
    password_hash: str
    created_at: datetime
    verified: bool
    user_roles: list[str]


class AuthRepository:
    """Repository for handling user database authentication operations.

    This class provides methods for user register, login, logout,
    and verify refresh tokens.

    It interfaces with the database and handles authentication-related business logic.

    Attributes:
        db_session: Database session for executing queries
    """

    def __init__(self, db: AsyncDatabase):
        self.db = db

    async def get_user_by_username(self, username: str) -> UserDict | None:
        """Return a user row by username, including roles."""
        query = load_sql_query("get_user_by_username", module="auth")
        return await self.db.fetchone(query, {"username": username})

    async def get_user_by_identifier(self, identifier: str) -> UserDict | None:
        """Return a user row by username or email, including roles."""
        query = load_sql_query("get_user_by_identifier", module="auth")
        return await self.db.fetchone(query, {"identifier": identifier})

    async def insert_user(
        self,
        *,
        username: str,
        email: str,
        slug: str,
        display_name: str | None,
        password_hash: str,
    ) -> None:
        """Insert a new user record."""
        query = load_sql_query("insert_user", module="auth")
        await self.db.fetchone(
            query,
            params={
                "username": username,
                "email": email,
                "slug": slug,
                "display_name": display_name,
                "password_hash": password_hash,
            },
        )

    async def verify_refresh_token(self, username: str, token: str) -> bool:
        """Return whether the refresh token belongs to the user and is still valid."""
        query = load_sql_query("verify_refresh_token", module="auth")
        result = await self.db.fetchone(query, params={"username": username, "refresh_token": token})
        return bool(result and result.get("valid", False))

    async def insert_refresh_token(self, username: str, refresh_token: str) -> int:
        """Store a refresh token for the user and update their last-login time."""
        params = {"username": username, "refresh_token": refresh_token}
        return await self.db.execute(load_sql_query("insert_refresh_token", module="auth"), params=params)

    async def update_user_password(self, username: str, password_hash: str) -> None:
        """Replace a user's password hash."""
        params = {"username": username, "password_hash": password_hash}
        await self.db.execute(load_sql_query("update_user_password", module="auth"), params=params)

    async def logout_user(self, username: str) -> None:
        """Delete every refresh token belonging to the user."""
        await self.db.execute(load_sql_query("logout_user", module="auth"), params={"username": username})
