from dataclasses import dataclass

from app.core.db import AsyncDatabase
from app.auth.repositories import AuthRepository
from app.auth.utils import PasswordUtils, TokenInput, TokenType, TokenUtils
from app.auth.exceptions import InvalidTokenError, InvalidCredentialsError, UserAlreadyExistsError, MissingRoleError
from app.auth.exceptions import UserNotFoundError
from app.auth.models import RegisterUser, ResponseUser, User

from config import get_settings

settings = get_settings()

# =======================================================================
# Data Classes
# =======================================================================


@dataclass(frozen=True)
class RefreshedTokens:
    """A new access token issued from an existing refresh token.

    The refresh token is reused rather than rotated, so it is not included.
    """

    access_token: str
    expires_in: int
    refresh_expires_in: int


@dataclass(frozen=True)
class LoginTokens(RefreshedTokens):
    """A newly issued access/refresh token pair.

    Routes are responsible for turning this into an HTTP response and cookie.
    """

    refresh_token: str


# =======================================================================
# Service Layer
# =======================================================================


class CoreUserService:
    """Core authentication service for user registration, login, and token management."""

    def __init__(self, database: AsyncDatabase):
        self.user_repo = AuthRepository(database)
        self.password_utils = PasswordUtils()
        self.token_utils = TokenUtils()

    async def get_current_user(self, token: str) -> User:
        """Return the user identified by a valid access token."""
        payload = self.token_utils.decode_token(token)
        if payload.get("type") != TokenType.ACCESS:
            raise InvalidTokenError(detail="Invalid token type")

        user = await self.user_repo.get_user_by_username(payload.get("sub", ""))
        if user is None:
            raise InvalidTokenError()
        return User.model_validate(user)

    async def get_optional_current_user(self, token: str | None) -> User | None:
        """Extract current user from access token"""
        if not token:
            return None
        return await self.get_current_user(token)


class AuthenticationService(CoreUserService):
    """Core authentication service for user registration, login, and token management."""

    def __init__(self, database: AsyncDatabase):
        super().__init__(database)

    async def register_user(self, user_data: RegisterUser) -> ResponseUser:
        """Register a new user with proper password hashing."""
        existing_user = await self.user_repo.get_user_by_username(user_data.username)
        if existing_user:
            raise UserAlreadyExistsError()
        password_hash = self.password_utils.hash_password(user_data.password)
        await self.user_repo.insert_user(
            username=user_data.username,
            email=user_data.email,
            slug=user_data.slug,
            display_name=user_data.display_name,
            password_hash=password_hash,
        )

        created_user = await self.user_repo.get_user_by_username(user_data.username)
        if created_user is None:
            raise UserNotFoundError()
        return ResponseUser.model_validate(created_user)

    async def authenticate_user(self, identifier: str, password: str) -> User | None:
        """Authenticate user with identifier/password. Identifier can be username or email."""
        user = await self.user_repo.get_user_by_identifier(identifier)
        if not user or not self.password_utils.verify_password(password, user["password_hash"]):
            return None
        return User.model_validate(user)

    async def login_user(self, identifier: str, password: str) -> LoginTokens:
        """Authenticate a user and issue a new token pair.

        Identifier can be username or email. The refresh token is persisted so
        the caller can deliver it to the client as an HttpOnly cookie.
        """
        user = await self.authenticate_user(identifier, password)
        if not user:
            raise InvalidCredentialsError()

        token_data: TokenInput = {"sub": user.username, "roles": user.user_roles}
        refresh_token = self.token_utils.create_refresh_token(data=token_data)
        access_token = self.token_utils.create_access_token(data=token_data)
        await self.user_repo.insert_refresh_token(user.username, refresh_token)

        return LoginTokens(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=self.token_utils.seconds_until_expiry(access_token),
            refresh_expires_in=self.token_utils.seconds_until_expiry(refresh_token),
        )

    async def reset_password(self, username: str, new_password: str) -> None:
        """Reset user password (internal use)."""
        password_hash = self.password_utils.hash_password(new_password)
        await self.user_repo.update_user_password(username, password_hash)

    async def logout_user(self, token: str) -> None:
        """Logout user and invalidate token."""
        payload = self.token_utils.decode_token(token)
        await self.user_repo.logout_user(payload.get("sub", ""))

    async def verify_refresh_token(self, token: str) -> str:
        """Verify a refresh token and return a new access token."""
        payload = self.token_utils.decode_token(token)
        if payload.get("type") != TokenType.REFRESH:
            raise InvalidTokenError(detail="Invalid token type")

        username = payload.get("sub", "")
        verified = await self.user_repo.verify_refresh_token(username, token)
        if not verified:
            raise InvalidTokenError()

        return self.token_utils.create_access_token(data={"sub": username, "roles": payload.get("roles", [])})

    async def refresh_access_token(self, refresh_token: str) -> RefreshedTokens:
        """Exchange a valid refresh token for a new access token.

        The refresh token is reused (not rotated), so the returned token set
        does not contain a new refresh token.
        """
        new_access_token = await self.verify_refresh_token(refresh_token)
        return RefreshedTokens(
            access_token=new_access_token,
            expires_in=self.token_utils.seconds_until_expiry(new_access_token),
            refresh_expires_in=self.token_utils.seconds_until_expiry(refresh_token),
        )


class AuthorizationService(CoreUserService):
    """Handles authorization checks for the current authenticated user."""

    def __init__(self, database: AsyncDatabase):
        super().__init__(database)

    async def require_role(self, user: User, role: str) -> User:
        """Dependency factory to require specific role"""
        if role not in user.user_roles:
            raise MissingRoleError(detail="You do not have permission to perform this action.")
        return user

    async def logout_user(self, token: str) -> None:
        """Revoke every refresh token for the user identified by an access token."""
        user = await self.get_current_user(token)
        await self.user_repo.logout_user(user.username)
