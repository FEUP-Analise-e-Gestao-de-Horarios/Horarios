from http import HTTPStatus

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.errors import ApiError, ErrorResponse, NotAuthenticatedResponse
from src.core.schemas import SuccessResponse
from src.projects.models import Project
from src.projects.projects_db.dao import StatsDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.schemas import ProjectStatsResponse


class ProjectStatsView(View):
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        # -- Fetch project -----------------------------------------------------
        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ErrorResponse(
                status=HTTPStatus.NOT_FOUND,
                code=ApiError.PROJECTS_NOT_FOUND,
                message="Project not found.",
            )

        # -- Query overview stats from project DB ------------------------------
        with get_project_session(general_db(project_id)) as db_session:
            overview = StatsDAO(db_session).get_overview()

        return JsonResponse(
            SuccessResponse(
                message="Stats retrieved successfully",
                data=ProjectStatsResponse(
                    degrees=overview.degrees,
                    years=overview.years,
                    subjects=overview.subjects,
                    classes=overview.classes,
                    teachers=overview.teachers,
                    rooms=overview.rooms,
                    sessions=overview.sessions,
                ),
            ).model_dump(),
        )
