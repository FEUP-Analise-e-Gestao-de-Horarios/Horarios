from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.decorators import require_auth, require_project
from src.core.schemas import SuccessResponse
from src.projects.projects_db.dao import StatsDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.stats import StatsResponse


class ProjectStatsView(View):
    """API endpoint: return overview statistics for a project."""

    @require_auth
    @require_project
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        with get_project_session(general_db(project_id)) as db_session:
            overview = StatsDAO(db_session).get_overview()

            return JsonResponse(
                SuccessResponse(
                    message="Stats retrieved successfully",
                    data=StatsResponse.model_validate(overview, from_attributes=True),
                ).model_dump(),
            )
