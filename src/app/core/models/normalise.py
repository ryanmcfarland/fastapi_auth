"""String normalization utilities for model field validation."""

import re


def strip_whitespace(v: str | None) -> str | None:
    """Remove leading and trailing whitespace."""
    return v.strip() if isinstance(v, str) else v


def empty_string_to_none(v: str | None) -> str | None:
    """Convert empty strings to None."""
    if isinstance(v, str) and v == "":
        return None
    return v


def normalise_string_to_none(v: str | None) -> str | None:
    """Normalise string by stripping whitespace and converting empty strings to None."""
    v = strip_whitespace(v)
    return empty_string_to_none(v)


def normalise_name(v: str, *, lowercase=True, pattern="lowercase_alphanumeric_symbols") -> str:
    """Normalise and validate name format."""
    if not isinstance(v, str):
        raise TypeError("Input must be a string")
    if lowercase:
        v = v.lower()
    patterns = {
        "letters_only": (r"[a-zA-Z]+", "letters only"),
        "alphanumeric": (r"[a-zA-Z0-9]+", "letters and numbers"),
        "alphanumeric_symbols": (r"[a-zA-Z0-9_-]+", "letters, numbers, underscores, and hyphens"),
        "lowercase_alphanumeric_symbols": (r"[a-z0-9_-]+", "lowercase letters, numbers, underscores, and hyphens"),
        "letters_with_spaces": (r"^[A-Za-z]+(?: [A-Za-z]+)*$", "letters with spaces between words"),
        "alphanumeric_symbols_with_spaces": (r"^[a-zA-Z0-9_-]+(?: [a-zA-Z0-9_-]+)*$", "letters, numbers and underscores with spaces between words"),
    }
    regex, description = patterns.get(pattern, patterns["lowercase_alphanumeric_symbols"])
    if not re.fullmatch(regex, v):
        raise ValueError(f"Input can only contain {description}")
    return v
