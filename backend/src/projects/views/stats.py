from http import HTTPStatus

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.errors import ApiError, ErrorResponse
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
            return ErrorResponse(
                status=HTTPStatus.UNAUTHORIZED,
                code=ApiError.AUTH_NOT_AUTHENTICATED,
                message="User is not authenticated.",
            )

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
                    num_degrees=overview.num_degrees,
                    num_years=overview.num_years,
                    num_subjects=overview.num_subjects,
                    num_classes=overview.num_classes,
                    num_teachers=overview.num_teachers,
                    num_rooms=overview.num_rooms,
                    num_sessions=overview.num_sessions,
                ),
            ).model_dump(),
        )
