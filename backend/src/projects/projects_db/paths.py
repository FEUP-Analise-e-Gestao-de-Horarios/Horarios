from pathlib import Path

from django.conf import settings


def project_dir(proj_id: int) -> Path:
    """Return the root directory for a project's database files."""
    return Path(settings.PROJECTS_DB_PATH) / str(proj_id)


def general_db(proj_id: int) -> Path:
    """Return the path to the project's general database file."""
    return project_dir(proj_id) / "general_database.db"


def initial_db(proj_id: int) -> Path:
    """Return the path to the project's initial database file."""
    return project_dir(proj_id) / "initial_database.db"


def all_dbs(proj_id: int) -> list[Path]:
    """Return paths to all database files for a project."""

    # All DB files for a project — used when initializing or evicting all at once
    ALL_DB_NAMES = ("general_database.db", "initial_database.db")

    return [project_dir(proj_id) / name for name in ALL_DB_NAMES]
