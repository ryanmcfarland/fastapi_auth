import logging

from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional, Union

from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row

from config import get_settings

settings = get_settings()

log = logging.getLogger("core.db")


class AsyncDatabase:
    """
    Async database class using psycopg3 AsyncConnectionPool for FastAPI applications.

    Features:
    - Connection pooling with automatic connection management
    - Transaction support with context managers
    - Prepared statement caching
    - Proper error handling and logging
    - FastAPI lifecycle integration
    """

    def __init__(
        self,
        min_size: int = 2,
        max_size: int = 4,
        max_waiting: int = 0,
        max_lifetime: float = 3600,
        max_idle: float = 600,
        reconnect_timeout: float = 30,
    ):
        self.connection_string: str = settings.DATABASE_URL
        self.queries = {}
        self.pool: Optional[AsyncConnectionPool] = None
        self.pool_config = {
            "conninfo": self.connection_string,
            "min_size": min_size,
            "max_size": max_size,
            "max_waiting": max_waiting,
            "max_lifetime": max_lifetime,
            "max_idle": max_idle,
            "reconnect_timeout": reconnect_timeout,
            "open": False,
        }
        self.pool = AsyncConnectionPool(**self.pool_config)
        return

    async def initialize(self) -> None:
        """Initialize the connection pool. Call this during FastAPI startup."""
        try:
            await self.pool.open()
            log.info(f"Database pool initialized with {self.pool.min_size}-{self.pool.max_size} connections")
        except Exception as e:
            log.error(f"Failed to initialize database pool: {e}")
            raise

    async def close(self) -> None:
        """Close the connection pool. Call this during FastAPI shutdown."""
        if self.pool:
            await self.pool.close()
            log.info("Database pool closed")

    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool with automatic cleanup."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")

        async with self.pool.connection() as conn:
            try:
                yield conn
            except Exception as e:
                log.error(f"Database connection error: {e.__class__.__name__}({e})", exc_info=True)
                raise

    async def execute(self, query: str, params: Optional[Union[Dict[str, Any], List[Any]]] = None) -> None:
        """Execute query and fetch a single row."""
        async with self.get_connection() as conn:
            conn.row_factory = dict_row
            await conn.execute(query, params=params)
        return None

    async def fetchone(self, query: str, params: Optional[Union[Dict[str, Any], List[Any]]] = None) -> Optional[Dict[str, Any]]:
        """Execute query and fetch a single row."""
        async with self.get_connection() as conn:
            conn.row_factory = dict_row
            cursor = await conn.execute(query, params=params)
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def fetchall(self, query: str, params: Optional[Union[Dict[str, Any], List[Any]]] = None) -> List[Dict[str, Any]]:
        """Execute query and fetch all rows."""
        async with self.get_connection() as conn:
            conn.row_factory = dict_row
            cursor = await conn.execute(query, params=params)
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def health_check(self) -> bool:
        """Check if the database connection is healthy."""
        await self.fetchone("SELECT 1")
        return True

    @property
    def pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        if not self.pool:
            return {}

        return {"size": self.pool.size, "available": self.pool.available, "min_size": self.pool.min_size, "max_size": self.pool.max_size}
