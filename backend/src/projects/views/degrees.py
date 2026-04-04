from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.errors import (
    DegreeNotFoundResponse,
    NotAuthenticatedResponse,
    ProjectNotFoundResponse,
)
from src.core.schemas import SuccessResponse
from src.projects.models import Project
from src.projects.projects_db.dao import DegreeDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.degrees import (
    DegreeStatsResponse,
    ProjectDegreesResponse,
)


class ProjectDegreesView(View):
    """API endpoint: list all degrees with stats for a project."""

    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        # -- Fetch project -----------------------------------------------------
        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        # -- Query degrees with stats from project DB --------------------------
        with get_project_session(general_db(project_id)) as db_session:
            stats = DegreeDAO(db_session).get_all_with_stats()
            result = [DegreeStatsResponse.model_validate(s, from_attributes=True) for s in stats]

            return JsonResponse(
                SuccessResponse(
                    message="Degrees retrieved successfully",
                    data=ProjectDegreesResponse(degrees=result, count=len(result)),
                ).model_dump(),
            )


class ProjectDegreeView(View):
    """API endpoint: retrieve a single degree with stats."""

    def get(self, request: HttpRequest, project_id: int, degree_id: UUID) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        # -- Fetch project -----------------------------------------------------
        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        # -- Fetch degree with stats from project DB ---------------------------
        with get_project_session(general_db(project_id)) as db_session:
            degree = DegreeDAO(db_session).get_with_stats(degree_id)
            if degree is None:
                return DegreeNotFoundResponse()

            return JsonResponse(
                SuccessResponse(
                    message="Degree retrieved successfully",
                    data=DegreeStatsResponse.model_validate(degree, from_attributes=True),
                ).model_dump(),
            )
