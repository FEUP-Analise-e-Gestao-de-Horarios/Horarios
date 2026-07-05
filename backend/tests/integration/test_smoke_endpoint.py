"""End-to-end smoke test for the parallel-blocks candidates endpoint.

Proves the whole harness works together: a real HTTP request through the Django
test client, auth + ``require_project`` decorators, URL routing, and the
per-project SQLAlchemy DB read from the ``tmp_path`` the ``project_db`` fixture
override points ``settings.PROJECTS_DB_PATH`` at.
"""

from django.test import Client
from sqlalchemy.orm import Session

from src.projects.models import Project


def _candidates_url(project_id: int) -> str:
    return f"/api/projects/{project_id}/parallel-blocks/candidates"


def test_candidates_empty_db_returns_empty_data(
    auth_client: Client,
    project: Project,
    project_db: Session,
) -> None:
    """An authenticated request against an empty seeded DB returns ``data == []``."""
    response = auth_client.get(_candidates_url(project.pk))

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"] == []
    assert payload["message"]


def test_candidates_requires_authentication(
    project: Project,
    project_db: Session,
) -> None:
    """An unauthenticated client is rejected with 401 before touching the DB."""
    response = Client().get(_candidates_url(project.pk))

    assert response.status_code == 401
    assert response.json()["error"] == "auth.not_authenticated"


def test_candidates_unknown_project_returns_404(
    auth_client: Client,
    project: Project,
) -> None:
    """A project id with no matching row is rejected with 404 by ``require_project``."""
    missing_id = project.pk + 1000
    response = auth_client.get(_candidates_url(missing_id))

    assert response.status_code == 404
    assert response.json()["error"] == "projects.not_found"
