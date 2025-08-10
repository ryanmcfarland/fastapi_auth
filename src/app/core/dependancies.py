from app.core.db import AsyncDatabase, get_database


def get_db() -> AsyncDatabase:
    """Dependency to get database instance."""
    return get_database()
