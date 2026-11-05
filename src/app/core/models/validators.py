"""
Factory functions for creating Pydantic field validators.

N.B: The !r conversion flag calls repr() on the value, which returns a string representation.
It's equivalent to `repr(value)`.
"""

import logging
import re

from typing import Callable

from pydantic import field_validator, ValidationInfo

from app.core.models.normalise import normalise_string_to_none, strip_whitespace, normalise_name

log = logging.getLogger("models.validators")


def strip_whitespace_validator(value: str | None, info: ValidationInfo) -> str | None:
    """Strip leading and trailing whitespace."""
    log.debug("stripping whitespace for field %s with value: %r", info.field_name, value)
    return strip_whitespace(value)


def normalise_string_to_none_validator(value: str | None, info: ValidationInfo) -> str | None:
    """Convert empty/whitespace-only strings to None, strip others."""
    log.debug("normalising field %s with value %r", info.field_name, value)
    return normalise_string_to_none(value)


def password_strength_validator(password: str) -> str:
    """Validate password strength without hashing."""
    if not isinstance(password, str):
        raise ValueError("Password must be a string")
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters")
    if len(password) > 128:
        raise ValueError("Password too long, maximum length is 128 characters")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise ValueError("Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise ValueError("Password must contain at least one number")
    return password


def normalise_name_factory(
    lowercase: bool = True,
    pattern: str = "lowercase_alphanumeric_symbols",
) -> Callable:
    """Create a validator for username fields with optional lowercasing."""

    def normalise_name_validator(value: str | None, info: ValidationInfo) -> str:
        """Validate and normalise username format."""
        log.debug("normalising %s with value %r", info.field_name, value)
        try:
            return normalise_name(value, lowercase=lowercase, pattern=pattern)
        except (TypeError, ValueError) as e:
            raise ValueError(f"{info.field_name.capitalize()} is invalid: {e}") from e

    return normalise_name_validator
