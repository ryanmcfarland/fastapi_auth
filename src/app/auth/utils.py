from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Any, NotRequired, TypedDict, cast

import bcrypt
import jwt

from app.auth.exceptions import InvalidTokenError

from config import get_settings

settings = get_settings()


class TokenType(StrEnum):
    ACCESS = "access"
    REFRESH = "refresh"
    PASSWORD_RESET = "password_reset"


class TokenInput(TypedDict):
    """Fields supplied when creating any JWT."""

    sub: str  # Username (JWT subject claim)
    roles: NotRequired[list[str]]  # Optional user roles for access control


# Type definitions for token payloads
class TokenPayload(TokenInput, total=True):
    """Base schema for all JWT token payloads."""

    exp: int  # Expiration time (unix timestamp)
    type: TokenType  # Token type: "access", "refresh", or "password_reset"


class PasswordUtils:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


class TokenUtils:
    @staticmethod
    def create_access_token(
        data: TokenInput,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create a JWT access token."""
        expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.access_token_expire_minutes))
        to_encode: dict[str, Any] = {**data, "exp": expire, "type": TokenType.ACCESS}
        return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

    @staticmethod
    def create_refresh_token(
        data: TokenInput,
        expires_delta: timedelta = timedelta(days=settings.refresh_token_expire_days),
    ) -> str:
        """Create a JWT refresh token."""
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode: dict[str, Any] = {**data, "exp": expire, "type": TokenType.REFRESH}
        return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

    @staticmethod
    def create_password_reset_token(
        data: TokenInput,
        expires_delta: timedelta | None = None,
    ) -> str:
        """Create a JWT password reset token."""
        expire = datetime.now(timezone.utc) + (expires_delta or timedelta(hours=settings.password_reset_token_expire_hours))
        to_encode: dict[str, Any] = {**data, "exp": expire, "type": TokenType.PASSWORD_RESET}
        return jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)

    @staticmethod
    def seconds_until_expiry(token: str) -> int:
        """Return the remaining lifetime of a valid JWT in whole seconds.

        Args:
            token: A signed, unexpired JWT.

        Returns:
            Whole seconds until the token's ``exp`` claim, never negative.

        Raises:
            InvalidTokenError: If the token is malformed or already expired.
        """
        payload = TokenUtils.decode_token(token)
        return max(0, int(payload["exp"]) - int(datetime.now(timezone.utc).timestamp()))

    @staticmethod
    def decode_token(token: str) -> TokenPayload:
        """
        Decode and verify a JWT token.

        Raises:
            InvalidTokenError: If the token is invalid or expired.
            Exception: Re-raises other unexpected exceptions.
        """
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            return cast(TokenPayload, payload)
        except jwt.InvalidTokenError as exc:
            raise InvalidTokenError() from exc
