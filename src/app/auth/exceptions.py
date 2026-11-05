"""
Custom exceptions for authentication and authorization.

HTTP Status Code Guidelines:
- 401 (Unauthorized): "You need to authenticate" - missing/invalid credentials or tokens
- 403 (Forbidden): "You don't have permission" - authenticated but insufficient permissions
- 404 (Not Found): "The resource doesn't exist" - user or resource not found
- 409 (Conflict): "This conflicts with existing data" - duplicate user registration
"""

from app.core.exceptions import ServiceError


class InvalidTokenError(ServiceError):
    """Raised when a token is invalid, malformed, or has wrong type."""

    def __init__(self, detail: str = "Invalid or expired token", *, status_code: int = 401):
        super().__init__(detail=detail, status_code=status_code)


class InvalidCredentialsError(ServiceError):
    """Raised when username/password combination is invalid."""

    def __init__(self, detail: str = "Invalid credentials provided", *, status_code: int = 401):
        super().__init__(detail=detail, status_code=status_code)


class UserAlreadyExistsError(ServiceError):
    """Raised when attempting to register a username or email that already exists."""

    def __init__(self, detail: str = "Username or email already registered", *, status_code: int = 409):
        super().__init__(detail=detail, status_code=status_code)


class UserNotFoundError(ServiceError):
    """Raised when a user is not found in the database."""

    def __init__(self, detail: str = "User not found", *, status_code: int = 404):
        super().__init__(detail=detail, status_code=status_code)


class MissingRoleError(ServiceError):
    """Raised when user lacks required role for an operation."""

    def __init__(self, detail: str = "Insufficient permissions for this action", *, status_code: int = 403):
        super().__init__(detail=detail, status_code=status_code)


class UnauthorizedRequestError(ServiceError):
    """Raised when user is not authorized to perform a requested action."""

    def __init__(self, detail: str = "You are not authorized to perform this action", *, status_code: int = 403):
        super().__init__(detail=detail, status_code=status_code)
