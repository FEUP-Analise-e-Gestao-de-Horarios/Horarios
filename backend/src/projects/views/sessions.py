from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.decorators import require_auth, require_project
from src.core.schemas import SuccessResponse
from src.parser.utils import validate_query_params
from src.projects.projects_db.dao import SessionDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.sessions import SessionsQueryParams, SessionsResponse
from src.projects.views.schemas.week_blocks import WeekBlock


class ProjectSessionsView(View):
    """API endpoint: list session blocks for a project, filtered by year."""

    @require_auth
    @require_project
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        params, err = validate_query_params(SessionsQueryParams, request.GET)
        if err is not None:
            return err

        with get_project_session(general_db(project_id)) as db_session:
            session_dao = SessionDAO(db_session)

            fingerprints = session_dao.get_year_week_fingerprints(params.year_id)
            groups = WeekBlock.group_by_fingerprint(fingerprints)
            representative_weeks = [repr_week for _, repr_week in groups]

            representative_sessions = session_dao.get_by_year(
                params.year_id,
                includes=list(SessionDAO.Include),
                weeks=representative_weeks,
            )

            blocks = WeekBlock.from_groups(groups, representative_sessions)

            return JsonResponse(
                SuccessResponse(
                    message="Sessions retrieved successfully",
                    data=SessionsResponse(blocks=blocks),
                ).model_dump(),
            )
