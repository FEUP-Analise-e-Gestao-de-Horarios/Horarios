"""End-to-end tests for ``/api/projects/<pk>/parallel-blocks/finish``.

This endpoint is the single place that toggles
``Project.has_selected_parallel_sessions``. ``POST`` flips it to ``True`` -- the
frontend calls it when the user leaves via "Terminar", whether or not every
subject was confirmed -- so the home card stops routing back to this step.
``DELETE`` flips it back to ``False`` -- called by "Recomeçar" to start the step
over. Creating or clearing groups no longer touches the flag.

The flag lives on the Django ``Project`` row (not the per-project SQLAlchemy
file), so these tests need no seeded project data; they only assert the flag
transition and the usual auth/project/method guards.
"""

from django.test import Client

from src.projects.models import Project


# ---------------------------------------------------------------------------
# -- Local helpers
# ---------------------------------------------------------------------------
def _finish_url(project_id: int) -> str:
    """The finish URL (no trailing slash: ``parallel-blocks/finish``)."""
    return f"/api/projects/{project_id}/parallel-blocks/finish"


def _flag(project_id: int) -> bool:
    """Reload the Django ``Project`` and return its parallel-selection flag."""
    return Project.objects.get(pk=project_id).has_selected_parallel_sessions


# ---------------------------------------------------------------------------
# -- Happy path
# ---------------------------------------------------------------------------
def test_finish_flips_flag_true(auth_client: Client, project: Project) -> None:
    """A fresh project (flag False) -> POST finish -> 200 and flag True."""
    assert _flag(project.pk) is False

    response = auth_client.post(_finish_url(project.pk))

    assert response.status_code == 200
    assert response.json()["data"] is None
    assert _flag(project.pk) is True


def test_finish_is_idempotent(auth_client: Client, project: Project) -> None:
    """Calling finish twice keeps the flag True -- no error on the second call."""
    assert auth_client.post(_finish_url(project.pk)).status_code == 200
    assert auth_client.post(_finish_url(project.pk)).status_code == 200
    assert _flag(project.pk) is True


# ---------------------------------------------------------------------------
# -- Reset: DELETE clears the flag
# ---------------------------------------------------------------------------
def test_delete_clears_flag_false(auth_client: Client, project: Project) -> None:
    """A finished project -> DELETE finish -> 200 and flag back to False."""
    assert auth_client.post(_finish_url(project.pk)).status_code == 200
    assert _flag(project.pk) is True

    response = auth_client.delete(_finish_url(project.pk))

    assert response.status_code == 200
    assert response.json()["data"] is None
    assert _flag(project.pk) is False


def test_delete_on_unset_flag_is_noop(auth_client: Client, project: Project) -> None:
    """DELETE on an already-False flag -> 200, flag stays False (Recomeçar before finishing)."""
    assert _flag(project.pk) is False

    response = auth_client.delete(_finish_url(project.pk))

    assert response.status_code == 200
    assert _flag(project.pk) is False


# ---------------------------------------------------------------------------
# -- Decorators (auth / project) and routing
# ---------------------------------------------------------------------------
def test_unauthenticated_finish_rejected(project: Project) -> None:
    """Unauthenticated finish -> 401 before any write; flag untouched."""
    response = Client().post(_finish_url(project.pk))

    assert response.status_code == 401
    assert response.json()["error"] == "auth.not_authenticated"
    assert _flag(project.pk) is False


def test_unauthenticated_reset_rejected(auth_client: Client, project: Project) -> None:
    """Unauthenticated DELETE -> 401 before any write; a finished flag survives."""
    assert auth_client.post(_finish_url(project.pk)).status_code == 200

    response = Client().delete(_finish_url(project.pk))

    assert response.status_code == 401
    assert response.json()["error"] == "auth.not_authenticated"
    assert _flag(project.pk) is True


def test_unknown_project_finish_returns_404(auth_client: Client, project: Project) -> None:
    """Finish on a nonexistent project id -> 404 from require_project."""
    response = auth_client.post(_finish_url(project.pk + 1000))

    assert response.status_code == 404
    assert response.json()["error"] == "projects.not_found"


def test_wrong_http_method_returns_405(auth_client: Client, project: Project) -> None:
    """GET on the finish route -> 405; the flag stays False."""
    response = auth_client.get(_finish_url(project.pk))

    assert response.status_code == 405
    assert _flag(project.pk) is False
