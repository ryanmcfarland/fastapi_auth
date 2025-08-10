"""
# Required JWT Constants
SECRET_KEY
ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS
"""

import bcrypt
import jwt
import re

from typing import Optional

from fastapi import Request, HTTPException
from fastapi.security import OAuth2PasswordBearer
from fastapi.security.utils import get_authorization_scheme_param
from datetime import datetime, timedelta, timezone

from config import get_settings

settings = get_settings()


class OAuth2PasswordBearerWithCookie(OAuth2PasswordBearer):
    """Extends the OAuth2PasswordBearer class to retrieve short-lived access token either from headers or cookies"""

    async def __call__(self, request: Request) -> Optional[str]:
        # Try to get auth field from headers (will be None during a redirect)
        authorization = request.headers.get("Authorization")
        if authorization is not None:
            scheme, param = get_authorization_scheme_param(authorization)
            if not authorization or scheme.lower() != "bearer":
                if self.auto_error:
                    raise HTTPException(
                        status_code=404,
                        detail="Not authenticated",
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                else:
                    return None
            return param
        # No token in header. Try using cookie:
        if token := request.cookies.get("session", None):
            param = token
            return param
        else:
            raise HTTPException(
                status_code=404,
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )


oauth2_scheme = OAuth2PasswordBearerWithCookie(tokenUrl="auth/login", refreshUrl="auth/refresh")


class PasswordUtils:
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))

    @staticmethod
    def is_strong_password(password: str) -> tuple[bool, str]:
        """Check if password meets security requirements."""
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        if len(password) > 128:
            return False, "Password too long"
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain uppercase letter"
        if not re.search(r"[a-z]", password):
            return False, "Password must contain lowercase letter"
        if not re.search(r"\d", password):
            return False, "Password must contain a number"
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain a special character"
        return True, "Password is strong"


class TokenUtils:
    @staticmethod
    def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
        to_encode.update({"exp": expire, "type": "access"})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def create_refresh_token(data: dict, expires_delta: timedelta = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)):
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire, "type": "refresh"})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def decode_token(token: str):
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except (jwt.ExpiredSignatureError, jwt.JWTError):
            raise HTTPException(status_code=401, detail="Invalid token")
