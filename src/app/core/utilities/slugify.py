import re
from unidecode import unidecode


def slugify(text: str) -> str:
    """
    Convert text to a URL-friendly slug.

    Args:
        text: The text to convert to a slug

    Returns:
        A lowercase, hyphenated slug with special characters removed
    """
    slug = unidecode(text)
    slug = slug.lower()
    slug = re.sub(r"[^\w\s-]", "", slug)
    slug = slug.replace("_", "-")
    slug = re.sub(r"[-\s]+", "-", slug)
    slug = slug.strip("-")
    return slug
