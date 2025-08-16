import re

from datetime import datetime

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Optional, List


class Token(BaseModel):
    access_token: str
    token_type: str


class RegisterRequest(BaseModel):
    """Input model - receives plain text password."""

    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5, max_length=100)
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email format")
        return v.lower()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password strength without hashing."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 128:
            raise ValueError("Password too long, maximun length is 128 characters")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number")
        return v


class UserResponse(BaseModel):
    """Response model - excludes id & password."""

    username: str
    email: str
    user_roles: List[str]
    created_at: datetime


class User(BaseModel):
    """Database model - stores hashed password."""

    id: Optional[int] = None
    username: str
    email: str
    password_hash: str
    roles: List[str]
    is_active: bool = True
    created_at: Optional[str] = None
