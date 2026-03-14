import shutil
from pathlib import Path

from src.projects.projects_db.paths import all_dbs, project_dir
from src.projects.projects_db.registry import evict_engine, init_engine


def create_project_db(proj_id: int) -> Path:
    """Create directory and initialise SQLite databases for a new project."""
    path = project_dir(proj_id)

    # Evict stale engines if the project is being recreated
    for db_path in all_dbs(proj_id):
        evict_engine(db_path)

    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=False)

    try:
        for db_path in all_dbs(proj_id):
            init_engine(db_path)  # create_all + cache engine
    except Exception:
        shutil.rmtree(path, ignore_errors=True)
        raise

    return path


def delete_project_db(proj_id: int) -> None:
    """Evict engines and remove the project directory."""
    for db_path in all_dbs(proj_id):
        evict_engine(db_path)
    shutil.rmtree(project_dir(proj_id), ignore_errors=True)
