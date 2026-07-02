"""Integration tests for the project CRUD endpoints (``src.projects.views.project``).

These exercise the Django-ORM side of the API (the ``Project`` model), not the
per-project SQLite file, plus the create endpoint's side effects: provisioning
the project database and kicking off ingestion on a background thread.

* ``GET  /api/projects/``      — list every project.
* ``POST /api/projects/``      — create a project, provision its DB, start ingestion.
* ``GET  /api/projects/<id>``  — retrieve one project.
* ``PATCH /api/projects/<id>`` — rename.
* ``DELETE /api/projects/<id>``— delete the project and its DB.

The background ingestion thread is neutralised by patching ``threading.Thread``
so no scraping happens; the test only asserts the thread was wired up.
"""

import json
from pathlib import Path
from typing import Self

import pytest
from django.test import Client
from pytest_django.fixtures import SettingsWrapper

from src.projects.models import Project
from src.projects.projects_db.paths import general_db, project_dir
from src.users.models import User


def _projects_url() -> str:
    return "/api/projects/"


def _project_url(project_id: int) -> str:
    return f"/api/projects/{project_id}"


@pytest.fixture
def no_ingestion_thread(monkeypatch: pytest.MonkeyPatch) -> list:
    """Replace the create endpoint's ``threading.Thread`` so ingestion never runs.

    Returns the list of constructed fake threads so a test can assert one was
    wired up (target callable, ``daemon=True``, ``start()`` called) without any
    scraping actually happening.
    """
    instances: list = []

    class _FakeThread:
        def __init__(self, *, target=None, daemon=None) -> None:
            self.target = target
            self.daemon = daemon
            self.started = False
            instances.append(self)

        def start(self) -> None:
            self.started = True

    monkeypatch.setattr("src.projects.views.project.threading.Thread", _FakeThread)
    return instances


@pytest.fixture
def db_path(settings: SettingsWrapper, tmp_path: Path) -> Path:
    """Point the project-DB root at an isolated tmp dir for create/delete."""
    settings.PROJECTS_DB_PATH = tmp_path
    return tmp_path


# ---------------------------------------------------------------------------
# -- List
# ---------------------------------------------------------------------------


def test_list_unauthenticated_returns_401(db: None) -> None:
    response = Client().get(_projects_url())
    assert response.status_code == 401
    assert response.json()["error"] == "auth.not_authenticated"


def test_list_empty(auth_client: Client) -> None:
    response = auth_client.get(_projects_url())
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["projects"] == []
    assert data["count"] == 0


def test_list_returns_projects(auth_client: Client, project: Project) -> None:
    response = auth_client.get(_projects_url())
    data = response.json()["data"]
    assert data["count"] == 1
    (entry,) = data["projects"]
    assert entry["id"] == project.pk
    assert entry["name"] == "Test Project"
    assert entry["has_selected_parallel_sessions"] is False


# ---------------------------------------------------------------------------
# -- Create
# ---------------------------------------------------------------------------


def _create(client: Client, **payload: object):
    return client.post(
        _projects_url(),
        data=json.dumps(payload),
        content_type="application/json",
    )


def test_create_unauthenticated_returns_401(db: None) -> None:
    response = _create(Client(), name="New", url="https://example.com/s")
    assert response.status_code == 401


def test_create_success_provisions_db_and_starts_ingestion(
    auth_client: Client,
    no_ingestion_thread: list,
    db_path: Path,
) -> None:
    response = _create(auth_client, name="Fresh Project", url="https://example.com/sched")

    assert response.status_code == 202
    data = response.json()["data"]
    assert data["name"] == "Fresh Project"

    project = Project.objects.get(pk=data["id"])
    assert project.creator_id is not None
    # The per-project DB was provisioned on disk.
    assert project_dir(project.pk).is_dir()
    assert general_db(project.pk).exists()
    # A daemon ingestion thread was wired up (but not executed by the fake).
    assert len(no_ingestion_thread) == 1
    thread = no_ingestion_thread[0]
    assert thread.daemon is True
    assert callable(thread.target)
    assert thread.started is True


def test_create_duplicate_name_returns_400(
    auth_client: Client,
    project: Project,
    no_ingestion_thread: list,
    db_path: Path,
) -> None:
    response = _create(auth_client, name=project.name, url="https://example.com/s")
    assert response.status_code == 400
    assert response.json()["error"] == "projects.create.duplicated_name"
    # No extra project or thread was created.
    assert Project.objects.count() == 1
    assert no_ingestion_thread == []


def test_create_invalid_url_returns_400(
    auth_client: Client,
    no_ingestion_thread: list,
    db_path: Path,
) -> None:
    response = _create(auth_client, name="Valid Name", url="not-a-url")
    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"
    assert Project.objects.count() == 0


def test_create_invalid_name_characters_returns_400(
    auth_client: Client,
    no_ingestion_thread: list,
    db_path: Path,
) -> None:
    response = _create(auth_client, name="bad/name!", url="https://example.com/s")
    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"


def test_create_malformed_json_returns_400(
    auth_client: Client,
    no_ingestion_thread: list,
    db_path: Path,
) -> None:
    response = auth_client.post(
        _projects_url(),
        data="{not json",
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"


def test_create_db_provision_failure_rolls_back(
    auth_client: Client,
    no_ingestion_thread: list,
    db_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(_proj_id: int) -> None:
        raise RuntimeError("disk full")

    monkeypatch.setattr("src.projects.views.project.create_project_db", boom)

    response = _create(auth_client, name="Doomed", url="https://example.com/s")

    assert response.status_code == 500
    assert response.json()["error"] == "projects.create.failed"
    # The half-created project row was rolled back.
    assert Project.objects.filter(name="Doomed").count() == 0


def _run_thread_synchronously(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch ``threading.Thread`` so ``start()`` runs the target inline."""

    class _SyncThread:
        def __init__(self, *, target=None, daemon=None) -> None:
            self._target = target

        def start(self) -> None:
            if self._target is not None:
                self._target()

    monkeypatch.setattr("src.projects.views.project.threading.Thread", _SyncThread)


def test_create_runs_ingestion_in_background(
    auth_client: Client,
    db_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The thread target drives ``IngestionManager`` as a context manager."""
    calls: list[int] = []

    class _NoopManager:
        def __init__(self, *, proj_id: int) -> None:
            self.proj_id = proj_id

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *exc: object) -> bool:
            return False

        def run(self) -> None:
            calls.append(self.proj_id)

    monkeypatch.setattr("src.projects.views.project.IngestionManager", _NoopManager)
    _run_thread_synchronously(monkeypatch)

    response = _create(auth_client, name="Ingested", url="https://example.com/s")

    assert response.status_code == 202
    assert calls == [response.json()["data"]["id"]]


def test_create_swallows_ingestion_thread_errors(
    auth_client: Client,
    db_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """An exception inside the ingestion thread is logged, not propagated."""

    class _BoomManager:
        def __init__(self, *, proj_id: int) -> None:
            pass

        def __enter__(self) -> Self:
            return self

        def __exit__(self, *exc: object) -> bool:
            return False

        def run(self) -> None:
            raise RuntimeError("ingestion blew up")

    monkeypatch.setattr("src.projects.views.project.IngestionManager", _BoomManager)
    _run_thread_synchronously(monkeypatch)

    # The endpoint still returns 202 even though the background run raised.
    response = _create(auth_client, name="Resilient", url="https://example.com/s")
    assert response.status_code == 202


# ---------------------------------------------------------------------------
# -- Retrieve
# ---------------------------------------------------------------------------


def test_detail_unauthenticated_returns_401(db: None) -> None:
    response = Client().get(_project_url(1))
    assert response.status_code == 401


def test_detail_unknown_returns_404(auth_client: Client) -> None:
    response = auth_client.get(_project_url(999_999))
    assert response.status_code == 404
    assert response.json()["error"] == "projects.not_found"


def test_detail_returns_project(auth_client: Client, project: Project) -> None:
    response = auth_client.get(_project_url(project.pk))
    assert response.status_code == 200
    data = response.json()["data"]
    assert data["id"] == project.pk
    assert data["name"] == "Test Project"
    assert data["url"] == "https://example.com/schedule"
    assert data["ingestion_started_at"] is None


# ---------------------------------------------------------------------------
# -- Rename
# ---------------------------------------------------------------------------


def _rename(client: Client, project_id: int, name: str):
    return client.patch(
        _project_url(project_id),
        data=json.dumps({"name": name}),
        content_type="application/json",
    )


def test_rename_unknown_returns_404(auth_client: Client) -> None:
    response = _rename(auth_client, 999_999, "Whatever")
    assert response.status_code == 404
    assert response.json()["error"] == "projects.not_found"


def test_rename_success(auth_client: Client, project: Project) -> None:
    response = _rename(auth_client, project.pk, "Renamed Project")
    assert response.status_code == 200
    assert response.json()["data"]["name"] == "Renamed Project"
    project.refresh_from_db()
    assert project.name == "Renamed Project"


def test_rename_duplicate_name_returns_400(auth_client: Client, user: User) -> None:
    a = Project.objects.create(name="Alpha", url="https://e.com/a", creator=user)
    Project.objects.create(name="Beta", url="https://e.com/b", creator=user)

    response = _rename(auth_client, a.pk, "Beta")
    assert response.status_code == 400
    assert response.json()["error"] == "projects.rename.duplicated_name"


def test_rename_to_same_name_is_allowed(auth_client: Client, project: Project) -> None:
    """Excluding self from the uniqueness check lets a no-op rename succeed."""
    response = _rename(auth_client, project.pk, project.name)
    assert response.status_code == 200


def test_rename_invalid_name_returns_400(auth_client: Client, project: Project) -> None:
    response = _rename(auth_client, project.pk, "x" * 31)
    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"


# ---------------------------------------------------------------------------
# -- Delete
# ---------------------------------------------------------------------------


def test_delete_unknown_returns_404(auth_client: Client, db_path: Path) -> None:
    response = auth_client.delete(_project_url(999_999))
    assert response.status_code == 404
    assert response.json()["error"] == "projects.not_found"


def test_delete_removes_project_and_db(
    auth_client: Client,
    project: Project,
    db_path: Path,
) -> None:
    # Provision the project dir so delete has something to remove.
    project_dir(project.pk).mkdir(parents=True, exist_ok=True)
    (project_dir(project.pk) / "marker").write_text("x")

    response = auth_client.delete(_project_url(project.pk))

    assert response.status_code == 200
    assert response.json()["message"] == "Project deleted successfully"
    assert Project.objects.filter(pk=project.pk).count() == 0
    assert not project_dir(project.pk).exists()
