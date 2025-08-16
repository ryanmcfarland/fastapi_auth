import bcrypt
import jwt

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
            # docs (Authorize) creates header : "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            scheme, param = get_authorization_scheme_param(authorization)
            if not authorization or scheme.lower() != "bearer":
                if self.auto_error:
                    raise HTTPException(status_code=401, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})
                else:
                    return None
            return param
        # No token in Authorization header. Try using cookie:
        if token := request.cookies.get("access_token", None):
            return token
        else:
            raise HTTPException(status_code=401, detail="Not authenticated", headers={"WWW-Authenticate": "Bearer"})


# Note (asof 2025-08-16) refreshUrl parameter is not used
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
