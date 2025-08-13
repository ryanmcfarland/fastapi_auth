from .db import AsyncDatabase

_db: AsyncDatabase = None


async def initialize_database():
    """Initialize the database connection."""
    global _db
    _db = AsyncDatabase()
    await _db.initialize()


async def close_database():
    """Close the database connection."""
    global _db
    if _db:
        await _db.close()
        _db = None


def get_database() -> AsyncDatabase:
    """Get the database instance."""
    if _db is None:
        raise RuntimeError("Database not initialized")
    return _db
