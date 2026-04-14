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
from src.projects.projects_db.dao import RoomDAO, RoomRedBlockDAO, SessionDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.rooms import (
    ProjectRoomsResponse,
    RoomDetailResponse,
    RoomStatsResponse,
)
from src.projects.views.schemas.shared import SessionResponse


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
                    data=ProjectRoomsResponse(rooms=result, count=len(result)),
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

            sessions = [
                SessionResponse.from_session(s) for s in SessionDAO(db_session).get_by_room(room_id)
            ]
            red_blocks = RoomRedBlockDAO(db_session).get_by_room(room_id)

            return JsonResponse(
                SuccessResponse(
                    message="Room retrieved successfully",
                    data=RoomDetailResponse.model_validate_with_extras(
                        room,
                        extras={"sessions": sessions, "red_blocks": red_blocks},
                    ),
                ).model_dump(),
            )
