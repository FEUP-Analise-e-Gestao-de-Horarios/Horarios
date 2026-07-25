"""Integration-scoped fixtures for the exporter pipeline.

The exporter needs *two* per-project SQLAlchemy databases (``initial`` and
``general``) under the same ``PROJECTS_DB_PATH`` root, whereas the shared
``project_db`` fixture only provisions ``general``. ``export_dbs`` mirrors
``project_db`` but builds both files and hands back a live session for each,
so a test can seed a baseline and an edited timetable and then drive either the
``ExportGraph`` directly or the ``/export`` endpoint.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import pytest
from pytest_django.fixtures import SettingsWrapper
from sqlalchemy.orm import Session

from src.projects.models import Project
from src.projects.projects_db.paths import general_db, initial_db, project_dir
from src.projects.projects_db.registry import evict_engine, get_session, init_engine


@dataclass
class ExportDBs:
    """Handles for one project's initial and general timetable databases."""

    project: Project
    project_id: int
    general: Session
    initial: Session


@pytest.fixture
def export_dbs(
    project: Project,
    settings: SettingsWrapper,
    tmp_path: Path,
) -> Iterator[ExportDBs]:
    """Provision the initial + general project databases and yield both sessions.

    Seeded rows must be committed (the factories commit by default) before the
    endpoint or a fresh ``ExportGraph`` opens its own session against the same
    files.
    """
    settings.PROJECTS_DB_PATH = tmp_path

    general_path = general_db(project.pk)
    initial_path = initial_db(project.pk)
    project_dir(project.pk).mkdir(parents=True, exist_ok=True)
    init_engine(general_path)
    init_engine(initial_path)

    general = get_session(general_path)
    initial = get_session(initial_path)
    try:
        yield ExportDBs(
            project=project,
            project_id=project.pk,
            general=general,
            initial=initial,
        )
    finally:
        general.close()
        initial.close()
        evict_engine(general_path)
        evict_engine(initial_path)
