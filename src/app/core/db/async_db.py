"""
Database module providing async PostgreSQL connection management.

This module wraps psycopg3's AsyncConnectionPool to provide a clean async interface
for executing database queries. It handles connection pooling, error mapping to custom
exceptions, and includes health checking and monitoring capabilities.

Key features:
- Async-first design with context managers for safe connection handling
- Automatic error mapping (UniqueViolation, ForeignKeyViolation, etc.) to custom exceptions
- Configurable connection pool with min/max size, idle timeout, and lifetime limits
- Background monitoring task that periodically logs pool statistics
- Health check endpoint for readiness/liveness probes
"""

from __future__ import annotations

import asyncio
import logging
import functools

from contextlib import asynccontextmanager
from typing import Any, Callable, Concatenate, Awaitable, cast
from typing import AsyncGenerator, LiteralString

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool
from psycopg.rows import AsyncRowFactory, DictRow, dict_row
from psycopg.errors import UniqueViolation, ForeignKeyViolation, CheckViolation
from psycopg.errors import OperationalError, DatabaseError

from config import get_settings

from app.core.exceptions import GeneralError
from app.core.exceptions import UniqueConstraintError, ForeignKeyConstraintError, CheckConstraintError
from app.core.exceptions import DBOperationError

settings = get_settings()

log = logging.getLogger("core.db")

# ============================================================================
# Type Aliases (PEP 695 — lazy, resolve after AsyncDatabase is defined)
# ============================================================================

Row = dict[str, Any]
Params = dict[str, Any] | list[Any] | None

type RowQueryCallable[**P, R] = Callable[Concatenate["AsyncDatabase", P], Awaitable[R]]

# ============================================================================
# Decorators
# ============================================================================


def with_connection[**P, R](func: RowQueryCallable[P, R]) -> RowQueryCallable[P, R]:
    """Open a connection if the caller didn't supply one via `conn=`.

    Also translates raw psycopg errors to domain exceptions at the method boundary.
    This is the catch layer for conn-passing flows:
        the wrapper runs inside the caller's transaction body (below any yielded connection),
        so callers holding a `conn` can `except UniqueConstraintError`
        and actually receive the translated error.
    """

    @functools.wraps(func)
    async def wrapper(self: AsyncDatabase, *args: P.args, **kwargs: P.kwargs) -> R:
        try:
            if kwargs.get("conn") is not None:
                return await func(self, *args, **kwargs)
            async with self.get_connection(row_factory=dict_row) as conn:
                kwargs["conn"] = conn
                return await func(self, *args, **kwargs)
        except GeneralError:
            # Already a domain exception (possibly mapped by an inner call) —
            # never double-wrap.
            raise
        except UniqueViolation as e:
            log.warning(f"Unique constraint violation: %s", e)
            raise UniqueConstraintError(f"Unique constraint violation: {str(e)}", e) from e
        except ForeignKeyViolation as e:
            log.warning(f"Foreign key constraint violation: %s", e)
            raise ForeignKeyConstraintError(f"Foreign key constraint violation: {str(e)}", e) from e
        except CheckViolation as e:
            log.warning(f"Check constraint violation: %s", e)
            raise CheckConstraintError(f"Check constraint violation: {str(e)}", e) from e
        except (DatabaseError, OperationalError) as e:
            log.error(f"OperationalError during DB operation: %s(%s)", e.__class__.__name__, e, exc_info=True)
            raise DBOperationError(f"Database operational error occurred: {e.__class__.__name__}({e})", original_error=e) from e

    return wrapper


# ============================================================================
# Runtime Guards & Query Compilation
# ============================================================================


def _connection(conn: AsyncConnection[DictRow] | None) -> AsyncConnection[DictRow]:
    """Narrow a possibly-injected @with_connection connection for type checkers."""
    if conn is None:  # guaranteed by @with_connection
        raise RuntimeError("conn should be set by @with_connection")
    return conn


def _as_literal(query: str) -> LiteralString:
    """Cast loaded SQL to LiteralString for psycopg's type checking.

    Queries come from load_sql_query / trusted internal sources — psycopg
    type-checks dynamic strings against injection risks, so this narrows the
    static type only.
    """
    return cast(LiteralString, query)


# ============================================================================
# Async Database Class
# ============================================================================


class AsyncDatabase:
    """
    Async database class using psycopg3 AsyncConnectionPool.

    Description:
    - min_size - pool maintains these connections at all times
    - max_size - pool can grow up to 4 connections
    - max_waiting - how many clients can queue for a connection until one frees up
    - max_lifetime - how long a connection can exist before being refreshed
    - max_idle - how long a connection exists until being closed
    - reconnect_timeout - how long to wait before trying to reconnect after a connection failure
    - **kwargs - additional keyword arguments to pass to AsyncConnectionPool (e.g. ssl, timeout, etc.)
        - (optional) prepare_threshold - how many times a query can be executed before being prepared (default: 5, set to None to disable)
    """

    def __init__(
        self,
        min_size: int = 2,
        max_size: int = 4,
        max_waiting: int = 0,
        max_lifetime: float = 3600,
        max_idle: float = 600,
        reconnect_timeout: float = 30,
        connection_string: str | None = None,
        **kwargs: Any,
    ):
        self.connection_string: str = connection_string or settings.database_url
        self._stats_task: asyncio.Task[None] | None = None
        self.pool_config: dict[str, Any] = {
            "min_size": min_size,
            "max_size": max_size,
            "max_waiting": max_waiting,
            "max_lifetime": max_lifetime,
            "max_idle": max_idle,
            "reconnect_timeout": reconnect_timeout,
        }
        self.pool: AsyncConnectionPool = AsyncConnectionPool(self.connection_string, **self.pool_config, open=False, kwargs=kwargs)

    async def initialize(self) -> None:
        """Initialize the connection pool. Call this during FastAPI startup."""
        try:
            await self.pool.open()
            log.info(f"Database pool initialized with {self.pool.min_size}-{self.pool.max_size} connections")
            # Start a background task to periodically log pool stats for monitoring
            self._stats_task = asyncio.create_task(self._log_pool_stats_periodically())
        except Exception as e:
            log.error(f"Failed to initialize database pool: {type(e).__name__}({e})")
            raise

    async def close(self) -> None:
        """Close the connection pool. Call this during FastAPI shutdown."""
        # Cancel the stats logging task to prevent orphaned background tasks
        if self._stats_task and not self._stats_task.done():
            self._stats_task.cancel()
            try:
                await self._stats_task
            except asyncio.CancelledError:
                pass
        if self.pool:
            await self.pool.close()
            log.info("Database pool closed")

    @asynccontextmanager
    async def get_connection[RowT](
        self,
        row_factory: AsyncRowFactory[RowT] = dict_row,
    ) -> AsyncGenerator[AsyncConnection[RowT], None]:
        """Get a connection from the pool with automatic cleanup and error handling.

        Constraint violations (unique/foreign-key/check) are translated in with_connection, which wraps every db method call.
        This context manager is only a backstop for connection-scope failures that never pass through a query wrapper,
            such as connection loss or a failed commit at context exit.
        """
        if not self.pool:
            raise RuntimeError("Database pool not initialized")
        async with self.pool.connection() as pooled_conn:
            try:
                # The pool statically types connections with its default tuple
                # rows; we install our own factory here, so narrow the row type.
                conn = cast(AsyncConnection[RowT], pooled_conn)
                conn.row_factory = row_factory
                yield conn
            except GeneralError:
                raise
            except (DatabaseError, OperationalError) as e:
                log.error(f"OperationalError during DB operation: {e.__class__.__name__}({e})", exc_info=True)
                raise DBOperationError(f"Database operational error occurred: {e.__class__.__name__}({e})", original_error=e) from e
            finally:
                log.debug("Database connection attempt finished for pool: %s", self.pool.get_stats())

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[AsyncConnection[DictRow], None]:
        """Yield a connection wrapped in an explicit transaction."""
        async with self.get_connection(row_factory=dict_row) as conn:
            async with conn.transaction():
                yield conn

    @with_connection
    async def execute(
        self,
        query: str,
        params: Params = None,
        *,
        conn: AsyncConnection[DictRow] | None = None,
    ) -> int:
        """Execute query and return the number of rows affected."""
        cur = await _connection(conn).execute(_as_literal(query), params=params)
        return cur.rowcount

    @with_connection
    async def fetchone(
        self,
        query: str,
        params: Params = None,
        *,
        conn: AsyncConnection[DictRow] | None = None,
    ) -> Row | None:
        """Execute query and fetch a single row."""
        cursor = await _connection(conn).execute(_as_literal(query), params=params)
        row = await cursor.fetchone()
        return dict(row) if row else None

    @with_connection
    async def fetchone_or_raise(
        self,
        query: str,
        params: Params = None,
        *,
        conn: AsyncConnection[DictRow] | None = None,
    ) -> Row:
        row = await self.fetchone(query, params, conn=conn)
        if row is None:
            raise RuntimeError(f"Expected a row, got None for query: {query!r}")
        return row

    @with_connection
    async def fetchall(
        self,
        query: str,
        params: Params = None,
        *,
        conn: AsyncConnection[DictRow] | None = None,
    ) -> list[Row]:
        """Execute query and fetch all rows."""
        cursor = await _connection(conn).execute(_as_literal(query), params=params)
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

    async def health_check(self) -> bool:
        """Check if the database connection is healthy."""
        log.debug("Performing database health check")
        await self.fetchone("SELECT 1")
        return True

    @property
    def pool_stats(self) -> dict[str, Any]:
        """Get connection pool statistics."""
        if not self.pool:
            return {}
        return {"pool_stats": self.pool.get_stats(), "pool_config": self.pool_config}

    async def _log_pool_stats_periodically(self, interval: float = 60) -> None:
        """Log pool stats every interval seconds."""
        log.info("Starting periodic pool stats logging every %s seconds", interval)
        while True:
            await asyncio.sleep(interval)
            log.info("Pool stats: %s", self.pool.get_stats())
