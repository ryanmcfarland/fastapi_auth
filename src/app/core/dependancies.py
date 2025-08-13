from .db import AsyncDatabase

from .globals import get_database


def get_db() -> AsyncDatabase:
    """Dependency to get database instance."""
    return get_database()
