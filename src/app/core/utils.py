import logging

from functools import lru_cache
from pathlib import Path

from config import get_settings

log = logging.getLogger("core.utils")

settings = get_settings()


@lru_cache(maxsize=64)
def load_sql_query(
    query_name: str,
    module: str | tuple[str] | None = None,
    base_path: Path = settings.code_directory,
    query_dir: str | None = "sql_queries",
) -> str:
    """
    SQL loader with configurable base path parameter

    Usage:
    - Production: load_sql_query("query_name")
    - Single module: load_sql_query("query_name", module="auth")
    - Multiple modules: load_sql_query("query_name", module=("killteam", "requests"))
    - Tests: load_sql_query("query_name", module="auth", query_dir="tests/sql_queries")
    """
    if query_dir:
        base_path = base_path / query_dir

    if module:
        if isinstance(module, tuple):
            module_path = "/".join(module)
            query_path = base_path / module_path / f"{query_name}.sql"
        else:
            query_path = base_path / module / f"{query_name}.sql"
    else:
        query_path = base_path / f"{query_name}.sql"

    try:
        content = query_path.read_text(encoding="utf-8").strip()
        log.debug(f"Loaded SQL query: {query_name}")
        return content
    except FileNotFoundError:
        raise FileNotFoundError(f"SQL query not found: {query_path}")
    except Exception as e:
        log.error(f"Error loading SQL query {query_path} : {e}")
        raise
