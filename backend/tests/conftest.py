"""Shared pytest fixtures for the backend test suite.

Two data layers are exercised here (see ``tests/README.md``):

* The Django ORM (default sqlite), managed by ``pytest-django``. The ``user``,
  ``auth_client`` and ``project`` fixtures live on this layer.
* A per-project SQLAlchemy SQLite file, one directory per ``Project.pk`` under
  ``settings.PROJECTS_DB_PATH``. The ``project_db`` fixture points that setting
  at a throwaway ``tmp_path``, builds the schema, and hands back a live
  ``Session`` for seeding. The endpoint under test opens its *own* session
  against the same file, so seeded rows must be committed before the request.
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from django.test import Client
from pytest_django.fixtures import SettingsWrapper
from sqlalchemy.orm import Session

from src.projects.models import Project
from src.projects.projects_db.paths import general_db, project_dir
from src.projects.projects_db.registry import evict_engine, get_session, init_engine
from src.users.models import User


@pytest.fixture
def user(db: None) -> User:
    """Create and return an active ``users.User`` via the custom manager."""
    return User.objects.create_user(
        email="tester@example.com",
        username="tester",
        password="test-pass-1234",
        is_active=True,
    )


@pytest.fixture
def auth_client(user: User) -> Client:
    """A Django test client logged in as ``user`` (CSRF is bypassed by the client)."""
    client = Client()
    client.force_login(user)
    return client


@pytest.fixture
def project(user: User) -> Project:
    """A ``projects.Project`` row owned by ``user``; its integer pk is used in URLs."""
    return Project.objects.create(
        name="Test Project",
        url="https://example.com/schedule",
        creator=user,
    )


@pytest.fixture
def project_db(
    project: Project,
    settings: SettingsWrapper,
    tmp_path: Path,
) -> Iterator[Session]:
    """Provision the per-project SQLAlchemy DB and yield a session for seeding.

    Steps:

    1. Point ``settings.PROJECTS_DB_PATH`` at a unique ``tmp_path`` so
       ``paths.general_db(project.pk)`` (read at call time) resolves under it.
    2. Create the project directory and build the ORM schema with
       ``init_engine`` (runs ``Base.metadata.create_all``).
    3. Yield a live ``Session``. Callers seed rows and **must commit** (directly
       or via the factories, which commit by default) so the endpoint's own
       session can read the data.
    4. On teardown, close the session and ``evict_engine`` to dispose the cached
       engine keyed on this ``tmp_path``.
    """
    settings.PROJECTS_DB_PATH = tmp_path

    db_path = general_db(project.pk)
    project_dir(project.pk).mkdir(parents=True, exist_ok=True)
    init_engine(db_path)

    session = get_session(db_path)
    try:
        yield session
    finally:
        session.close()
        evict_engine(db_path)


@pytest.fixture
def other_user(db: None) -> User:
    """A second active ``users.User``, distinct from ``user``.

    Access to a project is *not* scoped to its creator (``require_project`` only
    checks existence), so this fixture exists to document that shared-access
    behavior end to end — a logged-in non-owner can still reach the data.
    """
    return User.objects.create_user(
        email="other@example.com",
        username="other",
        password="test-pass-1234",
        is_active=True,
    )


@pytest.fixture
def other_auth_client(other_user: User) -> Client:
    """A Django test client logged in as ``other_user`` (a non-owner)."""
    client = Client()
    client.force_login(other_user)
    return client


@pytest.fixture
def second_project(user: User) -> Project:
    """A second ``projects.Project`` owned by ``user``; used for cross-project isolation."""
    return Project.objects.create(
        name="Second Project",
        url="https://example.com/schedule-2",
        creator=user,
    )


@pytest.fixture
def second_project_db(
    second_project: Project,
    settings: SettingsWrapper,
    tmp_path: Path,
) -> Iterator[Session]:
    """Provision a *second* per-project SQLAlchemy DB and yield a session for seeding.

    Mirrors ``project_db`` but for ``second_project``, under the same
    ``tmp_path`` root, so a test can seed two independent project databases and
    assert that an id living in one never leaks into the other (each project has
    its own SQLite file). Safe to use alongside ``project_db`` in one test.
    """
    settings.PROJECTS_DB_PATH = tmp_path

    db_path = general_db(second_project.pk)
    project_dir(second_project.pk).mkdir(parents=True, exist_ok=True)
    init_engine(db_path)

    session = get_session(db_path)
    try:
        yield session
    finally:
        session.close()
        evict_engine(db_path)
