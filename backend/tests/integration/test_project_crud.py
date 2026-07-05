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
    # The rejected rename left the stored name untouched.
    a.refresh_from_db()
    assert a.name == "Alpha"


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


# ---------------------------------------------------------------------------
# -- Gap 1: rename with invalid characters exercises the regex branch
# ---------------------------------------------------------------------------


def test_rename_invalid_name_characters_returns_400(
    auth_client: Client,
    project: Project,
) -> None:
    """A short-but-illegal name reaches the ``field_validator`` regex branch.

    ``test_rename_invalid_name_returns_400`` uses ``'x' * 31`` which is rejected
    earlier by ``Field(max_length=30)``; ``'bad/name!'`` is length-valid so it
    exercises the regex ``ValueError`` at ``schemas/project.py:60`` instead.
    """
    original_name = project.name
    response = _rename(auth_client, project.pk, "bad/name!")

    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"
    # The illegal rename left the stored name untouched.
    project.refresh_from_db()
    assert project.name == original_name


# ---------------------------------------------------------------------------
# -- Gap 2: unsupported HTTP methods return 405
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "url"),
    [
        # ProjectsView defines only get/post.
        ("PATCH", _projects_url()),
        ("DELETE", _projects_url()),
        ("PUT", _projects_url()),
        # ProjectView defines only get/patch/delete.
        ("POST", _project_url(1)),
        ("PUT", _project_url(1)),
    ],
)
def test_unsupported_methods_return_405(
    auth_client: Client,
    method: str,
    url: str,
) -> None:
    """Methods a view does not implement fall through to Django's 405."""
    response = auth_client.generic(method, url)
    assert response.status_code == 405


# ---------------------------------------------------------------------------
# -- Gap 3: missing required fields in POST/PATCH bodies
# ---------------------------------------------------------------------------


def test_create_missing_url_returns_400(
    auth_client: Client,
    no_ingestion_thread: list,
    db_path: Path,
) -> None:
    response = _create(auth_client, name="No URL")
    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"
    assert Project.objects.count() == 0
    assert no_ingestion_thread == []


def test_create_missing_name_returns_400(
    auth_client: Client,
    no_ingestion_thread: list,
    db_path: Path,
) -> None:
    response = _create(auth_client, url="https://example.com/s")
    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"
    assert Project.objects.count() == 0
    assert no_ingestion_thread == []


def test_rename_empty_body_returns_400(
    auth_client: Client,
    project: Project,
) -> None:
    """An empty PATCH body is missing the required ``name`` field."""
    original_name = project.name
    response = auth_client.patch(
        _project_url(project.pk),
        data=json.dumps({}),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"
    project.refresh_from_db()
    assert project.name == original_name


def test_rename_empty_string_name_returns_400(
    auth_client: Client,
    project: Project,
) -> None:
    """An empty-string name fails the ``[...]+`` regex (needs >= 1 char)."""
    original_name = project.name
    response = _rename(auth_client, project.pk, "")
    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"
    project.refresh_from_db()
    assert project.name == original_name


# ---------------------------------------------------------------------------
# -- Gap 4: creator is the authenticated user; failure path starts no thread
# ---------------------------------------------------------------------------


def test_create_sets_creator_to_request_user_and_rollback_starts_no_thread(
    auth_client: Client,
    user: User,
    no_ingestion_thread: list,
    db_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Success wires the creator to ``request.user``; a provision failure adds no thread."""
    # -- Success path: the creator is exactly the authenticated user. -------
    response = _create(auth_client, name="Owned", url="https://example.com/s")
    assert response.status_code == 202
    project = Project.objects.get(pk=response.json()["data"]["id"])
    assert project.creator_id == user.pk
    # Exactly one ingestion thread was wired up for the successful create.
    assert len(no_ingestion_thread) == 1

    # -- Rollback path: DB provisioning fails, so no new thread is started. --
    def boom(_proj_id: int) -> None:
        raise RuntimeError("disk full")

    monkeypatch.setattr("src.projects.views.project.create_project_db", boom)
    failure = _create(auth_client, name="Doomed", url="https://example.com/s")

    assert failure.status_code == 500
    assert failure.json()["error"] == "projects.create.failed"
    assert Project.objects.filter(name="Doomed").count() == 0
    # The failure path started no additional thread (still just the one above).
    assert len(no_ingestion_thread) == 1


# ---------------------------------------------------------------------------
# -- Gap 5: parametrized accept/reject boundary for names and urls
# ---------------------------------------------------------------------------


# NOTE: ``' '`` (a single space) is intentionally absent from the invalid-name
# table: the regex char class ``[a-zA-Z0-9_\-: ]+`` includes a space, so a
# space-only name is *accepted* (length 1 <= 30). See the acceptance test below.
@pytest.mark.parametrize(
    "name",
    [
        "",  # empty: the ``+`` quantifier needs >= 1 char
        "a" * 31,  # over Field(max_length=30)
        "bad/name!",  # '/' and '!' not in the allowed set
        "emoji\U0001f600",  # emoji not in the allowed set
        "semi;colon",  # ';' not in the allowed set
        "tab\tname",  # control char not in the allowed set
        "new\nline",  # newline not in the allowed set
        "dot.name",  # '.' not in the allowed set
    ],
)
def test_create_rejects_invalid_names_parametrized(
    auth_client: Client,
    no_ingestion_thread: list,
    db_path: Path,
    name: str,
) -> None:
    response = _create(auth_client, name=name, url="https://example.com/s")
    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"
    assert Project.objects.count() == 0
    assert no_ingestion_thread == []


@pytest.mark.parametrize(
    "url",
    [
        "not-a-url",  # no scheme/host
        "ftp://x",  # HttpUrl allows only http/https
        "javascript:alert(1)",  # non-http scheme
        "http://",  # scheme without a host
        "",  # empty
        "example.com/s",  # missing scheme
    ],
)
def test_create_rejects_invalid_urls_parametrized(
    auth_client: Client,
    no_ingestion_thread: list,
    db_path: Path,
    url: str,
) -> None:
    response = _create(auth_client, name="Valid Name", url=url)
    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"
    assert Project.objects.count() == 0
    assert no_ingestion_thread == []


@pytest.mark.parametrize(
    "name",
    [
        "a",  # single letter
        " ",  # single space is allowed by the char class
        "a" * 30,  # exactly at the max_length boundary
        "Valid Name",  # spaces allowed
        "with_under-score",  # '_' and '-' allowed
        "colon:name",  # ':' allowed
        "MiEIC 2024",  # digits allowed
    ],
)
def test_create_accepts_valid_names_parametrized(
    auth_client: Client,
    no_ingestion_thread: list,
    db_path: Path,
    name: str,
) -> None:
    """Names within the allowed char class and length are accepted (202)."""
    response = _create(auth_client, name=name, url="https://example.com/s")
    assert response.status_code == 202
    assert response.json()["data"]["name"] == name
    assert Project.objects.filter(name=name).count() == 1


# ---------------------------------------------------------------------------
# -- Gap 6: PATCH/DELETE unauthenticated return 401
# ---------------------------------------------------------------------------


def test_rename_unauthenticated_returns_401(db: None) -> None:
    response = Client().patch(
        _project_url(1),
        data=json.dumps({"name": "Whatever"}),
        content_type="application/json",
    )
    assert response.status_code == 401
    assert response.json()["error"] == "auth.not_authenticated"


def test_delete_unauthenticated_returns_401(db: None) -> None:
    response = Client().delete(_project_url(1))
    assert response.status_code == 401
    assert response.json()["error"] == "auth.not_authenticated"


# ---------------------------------------------------------------------------
# -- Gap 7: delete idempotency / double-delete
# ---------------------------------------------------------------------------


def test_delete_is_not_idempotent_second_call_returns_404(
    auth_client: Client,
    project: Project,
    db_path: Path,
) -> None:
    """Deleting twice: the first call succeeds, the second sees no such project."""
    project_dir(project.pk).mkdir(parents=True, exist_ok=True)

    first = auth_client.delete(_project_url(project.pk))
    assert first.status_code == 200

    second = auth_client.delete(_project_url(project.pk))
    assert second.status_code == 404
    assert second.json()["error"] == "projects.not_found"

    assert Project.objects.count() == 0


def test_delete_without_provisioned_db_dir_succeeds(
    auth_client: Client,
    project: Project,
    db_path: Path,
) -> None:
    """Deleting a project whose per-project DB dir was never created does not raise."""
    # Deliberately do NOT create project_dir(project.pk).
    assert not project_dir(project.pk).exists()

    response = auth_client.delete(_project_url(project.pk))

    assert response.status_code == 200
    assert Project.objects.filter(pk=project.pk).count() == 0
    assert not project_dir(project.pk).exists()


# ---------------------------------------------------------------------------
# -- Gap 8: create persists the (normalized) url, verified via round-trip GET
# ---------------------------------------------------------------------------


def test_create_url_round_trips_through_get(
    auth_client: Client,
    no_ingestion_thread: list,
    db_path: Path,
) -> None:
    """The url sent to POST is stored and read back verbatim (path is not rewritten)."""
    sent_url = "https://example.com/sched"
    create = _create(auth_client, name="RoundTrip", url=sent_url)
    assert create.status_code == 202
    project_id = create.json()["data"]["id"]

    detail = auth_client.get(_project_url(project_id))
    assert detail.status_code == 200
    # Pydantic HttpUrl leaves an explicit path untouched (no trailing slash added).
    assert detail.json()["data"]["url"] == "https://example.com/sched"
    assert Project.objects.get(pk=project_id).url == "https://example.com/sched"


def test_create_bare_host_url_gains_trailing_slash(
    auth_client: Client,
    no_ingestion_thread: list,
    db_path: Path,
) -> None:
    """A host-only url is normalized by HttpUrl to gain a trailing slash before persistence."""
    create = _create(auth_client, name="BareHost", url="https://example.com")
    assert create.status_code == 202
    project_id = create.json()["data"]["id"]

    detail = auth_client.get(_project_url(project_id))
    assert detail.json()["data"]["url"] == "https://example.com/"
    assert Project.objects.get(pk=project_id).url == "https://example.com/"


# ---------------------------------------------------------------------------
# -- Gap 9: unknown/extra fields are silently ignored (schema has no extra=forbid)
# ---------------------------------------------------------------------------


def test_create_ignores_unknown_extra_fields(
    auth_client: Client,
    no_ingestion_thread: list,
    db_path: Path,
) -> None:
    response = _create(
        auth_client,
        name="Extra",
        url="https://example.com/s",
        bogus="ignored",
        creator=999,
    )
    assert response.status_code == 202
    assert response.json()["data"]["name"] == "Extra"
    assert Project.objects.filter(name="Extra").count() == 1


# ---------------------------------------------------------------------------
# -- Gap 10: wrong-typed name is rejected
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", [None, 123])
def test_create_rejects_wrong_typed_name(
    auth_client: Client,
    no_ingestion_thread: list,
    db_path: Path,
    name: object,
) -> None:
    response = _create(auth_client, name=name, url="https://example.com/s")
    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"
    assert Project.objects.count() == 0
    assert no_ingestion_thread == []


@pytest.mark.parametrize("name", [None, 123])
def test_rename_rejects_wrong_typed_name(
    auth_client: Client,
    project: Project,
    name: object,
) -> None:
    original_name = project.name
    response = auth_client.patch(
        _project_url(project.pk),
        data=json.dumps({"name": name}),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert response.json()["error"] == "generic.invalid_body"
    project.refresh_from_db()
    assert project.name == original_name
