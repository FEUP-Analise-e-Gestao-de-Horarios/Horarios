from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.errors import (
    NotAuthenticatedResponse,
    ProjectNotFoundResponse,
    RoomNotFoundResponse,
)
from src.core.schemas import SuccessResponse
from src.projects.models import Project
from src.projects.projects_db.dao import RoomDAO, SessionDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.rooms import (
    RoomDetailResponse,
    RoomsResponse,
    RoomStatsResponse,
)
from src.projects.views.schemas.sessions import WeekBlockResponse


class ProjectRoomsView(View):
    """API endpoint: list all rooms with stats for a project."""

    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        # -- Fetch project -----------------------------------------------------
        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        # -- Query rooms with stats from project DB ----------------------------
        with get_project_session(general_db(project_id)) as db_session:
            stats = RoomDAO(db_session).get_all_with_stats()
            result = [RoomStatsResponse.model_validate(s, from_attributes=True) for s in stats]

            return JsonResponse(
                SuccessResponse(
                    message="Rooms retrieved successfully",
                    data=RoomsResponse(rooms=result, count=len(result)),
                ).model_dump(),
            )


class ProjectRoomView(View):
    """API endpoint: retrieve a single room with its sessions and red blocks."""

    def get(self, request: HttpRequest, project_id: int, room_id: UUID) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        # -- Fetch project -----------------------------------------------------
        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        # -- Fetch room with sessions and red blocks from project DB -----------
        with get_project_session(general_db(project_id)) as db_session:
            room = RoomDAO(db_session).get(room_id)
            if room is None:
                return RoomNotFoundResponse()

            blocks = WeekBlockResponse.from_sessions(
                SessionDAO(db_session).get_by_room(
                    room_id,
                    includes=list(SessionDAO.Include),
                ),
            )

            return JsonResponse(
                SuccessResponse(
                    message="Room retrieved successfully",
                    data=RoomDetailResponse.model_validate_with_extras(
                        room,
                        extras={"blocks": blocks},
                    ),
                ).model_dump(),
            )
