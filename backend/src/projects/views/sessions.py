from http import HTTPStatus
from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.errors import (
    NotAuthenticatedResponse,
    ProjectNotFoundResponse,
    SessionNotFoundResponse,
)
from src.projects.models import Project
from src.projects.projects_db.dao import SessionDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session


class ProjectSessionView(View):
    """API endpoint: delete a single session from a project."""

    def delete(
        self,
        request: HttpRequest,
        project_id: int,
        session_id: str,
    ) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        # -- Fetch project -----------------------------------------------------
        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        # -- Delete session from project DB -----------------------------------
        with get_project_session(general_db(project_id)) as db_session:
            deleted = SessionDAO(db_session).delete_by_id(UUID(session_id))
            if not deleted:
                return SessionNotFoundResponse()

            db_session.commit()

        return JsonResponse(
            {"message": "Session deleted successfully"},
            status=HTTPStatus.OK,
        )
