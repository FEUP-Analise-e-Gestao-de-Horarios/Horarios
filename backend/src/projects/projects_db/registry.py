import sqlite3
import threading
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import ConnectionPoolEntry

# Ensure models are registered in Base.metadata
from src.projects.projects_db import models  # noqa: F401
from src.projects.projects_db.migrations import run_project_db_migrations

from .base import Base

_engines: dict[str, Engine] = {}
_lock = threading.Lock()


def _configure_engine(engine: Engine) -> None:
    """Apply SQLite pragmas on every new connection."""

    @event.listens_for(engine, "connect")
    def on_connect(dbapi_conn: sqlite3.Connection, _: ConnectionPoolEntry) -> None:
        dbapi_conn.execute("PRAGMA journal_mode=WAL")
        dbapi_conn.execute("PRAGMA foreign_keys=ON")
        dbapi_conn.execute("PRAGMA busy_timeout=5000")


def get_engine(db_path: str | Path) -> Engine:
    """Return a cached engine for the given SQLite file path."""
    key = str(db_path)
    if key not in _engines:
        with _lock:
            if key not in _engines:
                engine = create_engine(
                    f"sqlite:///{key}",
                    connect_args={"check_same_thread": False},
                )
                _configure_engine(engine)
                _engines[key] = engine
    return _engines[key]


def init_engine(db_path: str | Path) -> Engine:
    """Get engine and ensure the ORM schema exists (create_all is idempotent)."""
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    run_project_db_migrations(engine)
    return engine


def get_session(db_path: str | Path) -> Session:
    """Return a new SQLAlchemy Session for the given DB path."""
    return Session(get_engine(db_path))


def evict_engine(db_path: str | Path) -> None:
    """Dispose and remove the engine for a deleted project."""
    key = str(db_path)
    with _lock:
        engine = _engines.pop(key, None)
        if engine:
            engine.dispose()
