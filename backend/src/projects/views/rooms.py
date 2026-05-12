from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.decorators import require_auth, require_project
from src.core.errors import RoomNotFoundResponse
from src.core.schemas import SuccessResponse
from src.projects.projects_db.dao import RoomDAO, SessionDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.rooms import (
    RoomDetailResponse,
    RoomsResponse,
    RoomStatsResponse,
)
from src.projects.views.schemas.week_blocks import WeekBlock


class ProjectRoomsView(View):
    """API endpoint: list all rooms with stats for a project."""

    @require_auth
    @require_project
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        with get_project_session(general_db(project_id)) as db_session:
            stats = RoomDAO(db_session).get_all_with_stats()
            result = [RoomStatsResponse.model_validate(s) for s in stats]

            return JsonResponse(
                SuccessResponse(
                    message="Rooms retrieved successfully",
                    data=RoomsResponse(rooms=result),
                ).model_dump(),
            )


class ProjectRoomView(View):
    """API endpoint: retrieve a single room with its sessions and red blocks."""

    @require_auth
    @require_project
    def get(self, request: HttpRequest, project_id: int, room_id: UUID) -> HttpResponse:
        with get_project_session(general_db(project_id)) as db_session:
            room = RoomDAO(db_session).get(room_id)
            if room is None:
                return RoomNotFoundResponse()

            session_dao = SessionDAO(db_session)

            fingerprints = session_dao.get_by_room_week_fingerprints(room_id)
            groups = WeekBlock.group_by_fingerprint(fingerprints)
            representative_weeks = [repr_week for _, repr_week in groups]

            representative_sessions = session_dao.get_by_room(
                room_id,
                includes=list(SessionDAO.Include),
                weeks=representative_weeks,
            )

            blocks = WeekBlock.from_groups(groups, representative_sessions)

            return JsonResponse(
                SuccessResponse(
                    message="Room retrieved successfully",
                    data=RoomDetailResponse.model_validate_with_extras(
                        room,
                        extras={"blocks": blocks},
                    ),
                ).model_dump(),
            )
