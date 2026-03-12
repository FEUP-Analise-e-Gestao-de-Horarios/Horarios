import shutil
import sqlite3
from pathlib import Path

from django.conf import settings


def create_project_db(proj_id: int) -> Path:
    """Create the directory and SQLite databases for a new project.

    Creates a subdirectory under ``settings.PROJECTS_DB_PATH`` named after
    ``proj_id`` and initializes two SQLite databases (``general_database.db``
    and ``initial_database.db``) using the SQL schema at
    ``settings.DB_DIR/init_project_db.sql``. If any step fails the directory is
    removed before re-raising the exception.

    Args:
        proj_id: Unique identifier of the project.

    Returns:
        Path to the newly created project directory.

    Raises:
        Exception: Any error raised while reading the schema or initializing
            the databases (directory is cleaned up automatically).
    """

    path: Path = settings.PROJECTS_DB_PATH / str(proj_id)
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=False)

    try:
        schema: str = (settings.DB_DIR / "init_project_db.sql").read_text()
        for db_name in ("general_database.db", "initial_database.db"):
            conn = sqlite3.connect(path / db_name)
            conn.cursor().executescript(schema)
            conn.commit()
            conn.close()

    except Exception:
        shutil.rmtree(path, ignore_errors=True)
        raise

    return path
