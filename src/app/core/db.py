import logging

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from psycopg_pool import AsyncConnectionPool
from psycopg.rows import dict_row

from config import get_settings

settings = get_settings()

log = logging.getLogger("db")


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
        self.sql_directories: List[Path] = settings.SQL_DIRECTORIES
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
        self._load_queries()
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

    def _load_queries(self) -> None:
        for dir in self.sql_directories:
            self._load_queries_from_directory(dir)

    def _load_queries_from_directory(self, directory) -> None:
        """Load all .sql files from the specified directory."""
        log.debug(f"Loading .sql files from : {directory}")
        sql_files = directory.rglob("*.sql")

        for sql_file in sql_files:
            # Get relative path from base directory and create dotted key
            relative_path = sql_file.relative_to(directory)
            # Convert path to dotted notation: auth/get_user.sql -> auth.get_user
            path_parts = list(relative_path.parts[:-1])  # exclude filename
            filename_stem = sql_file.stem  # filename without extension
            if path_parts:
                query_name = ".".join(path_parts) + "." + filename_stem
            else:
                query_name = filename_stem
            try:
                with open(sql_file, "r", encoding="utf-8") as f:
                    query_content = f.read().strip()
                self.queries[query_name] = query_content
                log.debug(f"Loaded query: {query_name}")
            except Exception as e:
                log.debug(f"Error loading {sql_file}: {e}")

    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool with automatic cleanup."""
        if not self.pool:
            raise RuntimeError("Database pool not initialized")

        async with self.pool.connection() as conn:
            try:
                yield conn
            except Exception as e:
                log.error(f"Database connection error: {e}")
                raise

    async def execute(self, query: str, params: Optional[Union[Dict[str, Any], List[Any]]] = None) -> None:
        """Execute query and fetch a single row."""
        actual_query = self.get_query(query)
        async with self.get_connection() as conn:
            conn.row_factory = dict_row
            try:
                await conn.execute(actual_query, params=params)
            except Exception as e:
                log.error(f"Fetchone error: {e}")
                raise
        return None

    async def fetchone(self, query: str, params: Optional[Union[Dict[str, Any], List[Any]]] = None) -> Optional[Dict[str, Any]]:
        """Execute query and fetch a single row."""
        actual_query = self.get_query(query)
        async with self.get_connection() as conn:
            conn.row_factory = dict_row
            try:
                cursor = await conn.execute(actual_query, params=params)
                row = await cursor.fetchone()
                return dict(row) if row else None
            except Exception as e:
                log.error(f"Fetchone error: {e}")
                raise

    async def fetchall(self, query: str, params: Optional[Union[Dict[str, Any], List[Any]]] = None) -> List[Dict[str, Any]]:
        """Execute query and fetch all rows."""
        actual_query = self.get_query(query)
        async with self.get_connection() as conn:
            conn.row_factory = dict_row
            try:
                cursor = await conn.execute(actual_query, params=params)
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
            except Exception as e:
                log.error(f"Fetchall error: {e}")
                raise

    async def health_check(self) -> bool:
        """Check if the database connection is healthy."""
        try:
            await self.fetchone("SELECT 1")
            return True
        except Exception as e:
            log.error(f"Database health check failed: {e}")
            return False

    @property
    def pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics."""
        if not self.pool:
            return {}

        return {"size": self.pool.size, "available": self.pool.available, "min_size": self.pool.min_size, "max_size": self.pool.max_size}

    def get_query(self, query_name: str) -> str:
        """
        Get a specific query by name.

        Args:
            query_name (str): Name of the query (filename without .sql extension)

        Returns:
            str: The SQL query string

        Raises:
            KeyError: If query not found
        """
        if query_name not in self.queries:
            available_queries = list(self.queries.keys())
            raise KeyError(f"Query '{query_name}' not found. Available: {available_queries}")
        return self.queries[query_name]


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
