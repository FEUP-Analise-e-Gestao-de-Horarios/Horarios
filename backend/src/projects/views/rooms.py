from http import HTTPStatus

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.errors import ApiError, ErrorResponse, NotAuthenticatedResponse
from src.core.schemas import SuccessResponse
from src.projects.models import Project
from src.projects.projects_db.dao import RoomDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.rooms import ProjectRoomsResponse, RoomStatsResponse


class ProjectRoomsView(View):
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

        # -- Query rooms with stats from project DB ----------------------------
        with get_project_session(general_db(project_id)) as db_session:
            stats = RoomDAO(db_session).get_all_with_stats()
            result = [
                RoomStatsResponse(
                    id=str(s.id),
                    name=s.name,
                    type=s.type,
                    size=s.size,
                    seats=s.seats,
                    num_sessions=s.num_sessions,
                )
                for s in stats
            ]

        return JsonResponse(
            SuccessResponse(
                message="Rooms retrieved successfully",
                data=ProjectRoomsResponse(rooms=result, count=len(result)),
            ).model_dump(),
        )
