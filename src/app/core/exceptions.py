"""
Custom exceptions for the application.

Reference: https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status#client_error_responses

HTTP Status Code Guidelines:
- 400 (Bad Request): "You made the request wrong" - malformed request, invalid parameters
- 401 (Unauthorized): "You need to authenticate" - missing or invalid credentials
- 403 (Forbidden): "You don't have permission" - authenticated but not authorized
- 404 (Not Found): "The thing you're looking for doesn't exist" - valid request, missing resource
- 409 (Conflict): "This conflicts with existing data" - duplicate entries, state conflicts
- 422 (Unprocessable Entity): "Your data failed validation rules" - valid format, invalid business rules
"""

import logging

from typing import Any

log = logging.getLogger("core.exceptions")


class GeneralError(Exception):
    """A general exception for unexpected errors

    Args:
        detail: User-facing error message (e.g., "Internal Server Error", "Validation failed")
        message: Additional context for logging/debugging (e.g., "Duplicate record exists", "Foreign key constraint violated")
        status_code: HTTP status code to return (default: 500)
        errors: Field-specific error messages for frontend validation (e.g., {"email": "Already exists"})
        original_error: The underlying exception that caused this error, if any
    """

    def __init__(
        self,
        detail: str = "Internal Server Error",
        *,
        log_message: str | None = None,
        status_code: int = 500,
        errors: dict[str, str] | None = None,
        original_error: Exception | None = None,
    ):
        self.detail = detail
        self.log_message = log_message
        self.status_code = status_code
        self.errors = errors or {}
        self.original_error = original_error
        super().__init__(self.detail)

        self._log()

    @property
    def content(self) -> dict:
        """Return content dict for JSON response"""
        content: dict[str, Any] = {"detail": self.detail}
        if self.errors:
            content["errors"] = self.errors
        return content

    def _log(self) -> None:
        log_data = {"message": self.log_message or self.detail, "status_code": self.status_code}
        if self.status_code >= 500:
            log.error(log_data, exc_info=self.original_error)
        elif self.status_code >= 400:
            log.warning(log_data)
        else:
            log.debug(log_data)


class CustomValidationError(GeneralError):
    def __init__(self, errors: dict):
        super().__init__("Validation failed.", status_code=422, errors=errors)


########################
# Service-related exceptions
########################


class ServiceError(GeneralError):
    """Base exception for service errors"""

    def __init__(self, detail: str, *, status_code: int = 400, errors: dict | None = None, original_error: Exception | None = None):
        super().__init__(detail, status_code=status_code, errors=errors, original_error=original_error)


class InvalidParameterError(ServiceError):
    """Raised when request parameters are invalid"""

    def __init__(self, detail: str = "Invalid parameters provided."):
        super().__init__(detail=detail, status_code=400)


class UnauthorizedRequestError(ServiceError):
    """Raised when user tries to access a request they don't own"""

    def __init__(self, detail: str = "You are not authorized to access this request."):
        super().__init__(detail, status_code=403)


class RequestNotFoundError(ServiceError):
    """Raised when a request is not found or doesn't belong to the user"""

    def __init__(self, detail: str = "Request not found."):
        super().__init__(detail, status_code=404)


class ConflictError(ServiceError):
    """Raised when operation conflicts with existing data or state"""

    def __init__(self, detail: str, errors: dict | None = None):
        super().__init__(detail, status_code=409, errors=errors)


######################
# Database-related exceptions
######################


class DBOperationError(GeneralError):
    """Raised when a database operation fails"""

    def __init__(self, detail: str = "DB unavailable", *, log_message: str | None = None, status_code: int = 500, original_error: Exception | None = None):
        super().__init__(detail, log_message=log_message, status_code=status_code, original_error=original_error)


class UniqueConstraintError(DBOperationError):
    """Raised when a unique constraint is violated"""

    def __init__(self, message: str, original_error: Exception):
        super().__init__("This record already exists", log_message=message, status_code=409, original_error=original_error)


class ForeignKeyConstraintError(DBOperationError):
    """Raised when a foreign key constraint is violated"""

    def __init__(self, message: str, original_error: Exception):
        super().__init__("Referenced record does not exist", log_message=message, status_code=400, original_error=original_error)


class CheckConstraintError(DBOperationError):
    """Raised when a check constraint is violated"""

    def __init__(self, message: str, original_error: Exception):
        super().__init__("Data validation failed", log_message=message, status_code=400, original_error=original_error)
