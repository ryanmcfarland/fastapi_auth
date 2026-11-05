import functools
from typing import Any, Awaitable, Callable, Protocol, TypeVar, cast

from .async_db import AsyncDatabase

# Keeps track of the exact method signature being wrapped
F = TypeVar("F", bound=Callable[..., Awaitable[Any]])


class _HasTransactionalRepo(Protocol):
    db: AsyncDatabase


def transactional(func: F) -> F:
    """Ensure the wrapped service method runs with a database connection."""

    @functools.wraps(func)
    async def wrapper(self: _HasTransactionalRepo, *args: Any, **kwargs: Any) -> Any:
        conn = kwargs.pop("conn", None)

        if conn is not None:
            return await func(self, *args, conn=conn, **kwargs)

        # Ensure self has db at runtime (duck typing check)
        async with self.db.transaction() as new_conn:
            return await func(self, *args, conn=new_conn, **kwargs)

    # We cast to F to tell the type checker:
    # "The outside world sees the exact same method signature as the original function"
    return cast(F, wrapper)
