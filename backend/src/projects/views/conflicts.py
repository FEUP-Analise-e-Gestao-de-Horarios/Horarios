from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.decorators import require_auth, require_project
from src.core.schemas import SuccessResponse
from src.projects.projects_db.dao import SessionDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.services.conflict_detection import detect_conflicts
from src.projects.views.schemas.conflicts import ConflictsResponse


class ProjectConflictsView(View):
    """API endpoint: detect conflicts among all sessions in the project."""

    @require_auth
    @require_project
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        with get_project_session(general_db(project_id)) as db_session:
            sessions = SessionDAO(db_session).get_all(includes=list(SessionDAO.Include))

            conflicts = detect_conflicts(sessions)

            return JsonResponse(
                SuccessResponse(
                    message="Conflicts retrieved successfully",
                    data=ConflictsResponse(conflicts=conflicts, count=len(conflicts)),
                ).model_dump(),
            )
