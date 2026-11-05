import re

from datetime import datetime, timezone
from typing import Annotated, Optional, List

from pydantic import AliasChoices, BaseModel, Field, computed_field, field_validator, field_serializer
from pydantic import EmailStr, StringConstraints, BeforeValidator, AfterValidator

from app.core.models.validators import strip_whitespace_validator, normalise_string_to_none_validator, password_strength_validator
from app.core.models.validators import normalise_name_factory

from app.core.utilities.slugify import slugify

# ---------------------------------------------------------------------------
# Model Functions
# ---------------------------------------------------------------------------


def utc_now():
    return datetime.now(timezone.utc)


normalised_username_validator = normalise_name_factory(lowercase=True)

# ---------------------------------------------------------------------------
# Annotations
# Order of Operations: https://pydantic.dev/docs/validation/latest/concepts/validators/#ordering-of-validators
# ---------------------------------------------------------------------------

# Building blocks (private)
_StrippedStr = Annotated[str, BeforeValidator(strip_whitespace_validator)]
_NormalisedStr = Annotated[_StrippedStr, AfterValidator(normalised_username_validator)]

# Public types
Username = Annotated[_NormalisedStr, StringConstraints(min_length=3, max_length=50)]
DisplayName = Annotated[Optional[Annotated[_StrippedStr, StringConstraints(min_length=3, max_length=50)]], BeforeValidator(normalise_string_to_none_validator)]
ValidatedEmail = Annotated[EmailStr, BeforeValidator(strip_whitespace_validator), StringConstraints(min_length=5, max_length=128)]
StrongPassword = Annotated[str, BeforeValidator(password_strength_validator), StringConstraints(min_length=8, max_length=128)]


# ---------------------------------------------------------------------------
# Base User Models
# ---------------------------------------------------------------------------


class UserSummary(BaseModel):
    id: int = Field(..., validation_alias=AliasChoices("id", "user_id"))
    username: str
    slug: str
    display_name: str | None = None

    @field_serializer("display_name")
    def serialize_display_name(self, value: str | None) -> str:
        """Ensure display_name is empty unless serialized"""
        return value if value is not None else self.username


# ---------------------------------------------------------------------------
# Request Authentication Models
# ---------------------------------------------------------------------------


class RegisterUser(BaseModel):
    username: Username
    display_name: DisplayName = None
    email: ValidatedEmail
    password: Annotated[StrongPassword, Field(exclude=True)]

    @computed_field
    @property
    def slug(self) -> str:
        return slugify(self.username)


class PasswordResetRequest(BaseModel):
    """Request to initiate password reset."""

    email: ValidatedEmail


class PasswordResetConfirm(BaseModel):
    """Confirm password reset with token and new password."""

    token: str
    password: Annotated[StrongPassword, Field(exclude=True)]


class AdminResetPassword(BaseModel):
    """Admin request to reset user password."""

    username: Username
    password: Annotated[StrongPassword, Field(exclude=True)]


# ---------------------------------------------------------------------------
# Response Authentication Models
# ---------------------------------------------------------------------------


class AccessTokenPublic(BaseModel):
    """OAuth2-style token response.

    Lifetime metadata is expressed in seconds so clients do not need to
    duplicate the backend's token TTL configuration in order to set cookie
    ``Max-Age`` values.
    """

    access_token: str
    token_type: str
    expires_in: int = Field(..., description="Access token lifetime in seconds.")
    refresh_expires_in: int | None = Field(
        None,
        description="Remaining refresh token lifetime in seconds, when a refresh token is in play.",
    )


class ResponseUser(UserSummary):
    """Response model - excludes id & password."""

    id: int
    email: str
    user_roles: List[str]
    created_at: datetime

    @field_serializer("created_at", when_used="json")
    def serialize_created_at_json(self, dt: datetime, _info) -> str:
        """For JSON serialization - ISO format"""
        return dt.isoformat()


# ---------------------------------------------------------------------------
# Internal User Models
# ---------------------------------------------------------------------------


class User(ResponseUser):
    """Internal Database Model. Stores hashed password."""

    password_hash: str
    is_active: bool = True
    created_at: datetime = Field(default_factory=utc_now)
