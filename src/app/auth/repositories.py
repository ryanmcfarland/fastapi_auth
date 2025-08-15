from typing import Optional

from app.core.db import AsyncDatabase
from app.core.utils import load_sql_query


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

    async def get_user_by_username(self, username: str) -> Optional[dict]:
        query = load_sql_query("get_user_by_username", module="auth")
        return await self.db.fetchone(query, {"username": username})

    async def insert_user(self, username: str, email: str, password_hash: str) -> None:
        params = {"username": username, "email": email, "password_hash": password_hash}
        query = load_sql_query("insert_user", module="auth")
        await self.db.fetchone(query, params=params)
        return

    async def verify_refresh_token(self, username: str, token: str) -> bool:
        query = load_sql_query("verify_refresh_token", module="auth")
        return await self.db.fetchone(query, params={"username": username, "refresh_token": token})

    async def insert_refresh_token(self, username: str, refresh_token: str) -> dict:
        params = {"username": username, "refresh_token": refresh_token}
        return await self.db.execute(load_sql_query("insert_refresh_token", module="auth"), params=params)

    async def logout_user(self, user_id: int) -> None:
        return await self.db.execute(load_sql_query("logout_user", module="auth"), params={"user_id": user_id})
