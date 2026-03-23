from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.errors import NotAuthenticatedResponse, ProjectNotFoundResponse
from src.core.schemas import SuccessResponse
from src.projects.models import Project
from src.projects.projects_db.dao import StatsDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.stats import ProjectStatsResponse


class ProjectStatsView(View):
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        # -- Fetch project -----------------------------------------------------
        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        # -- Query overview stats from project DB ------------------------------
        with get_project_session(general_db(project_id)) as db_session:
            overview = StatsDAO(db_session).get_overview()

            return JsonResponse(
                SuccessResponse(
                    message="Stats retrieved successfully",
                    data=ProjectStatsResponse.model_validate(overview, from_attributes=True),
                ).model_dump(),
            )
