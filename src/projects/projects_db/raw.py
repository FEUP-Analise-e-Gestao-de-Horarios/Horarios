"""
Compatibility shim: lets existing code that uses raw sqlite3 strings
continue working, but routed through the SQLAlchemy engine cache
so connections are managed consistently.

Usage (drop-in for sqlite3.connect):

    from src.projects.projects_db.raw import raw_connection

    with raw_connection(db_path) as conn:
        conn.execute("SELECT * FROM old_table WHERE id = ?", (some_id,))
        conn.commit()
"""

# TODO Delete this when no longer necessary

from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy.pool import PoolProxiedConnection

from .registry import get_engine


@contextmanager
def raw_connection(db_path: str | Path) -> Generator[PoolProxiedConnection]:
    """
    Yield a raw DBAPI connection from the SQLAlchemy pool.
    Drop-in replacement for sqlite3.connect(db_path).
    Do NOT close the connection manually — it returns to the pool on exit.
    """
    engine = get_engine(db_path)
    conn = engine.raw_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()  # Returns to pool, does not close the file
