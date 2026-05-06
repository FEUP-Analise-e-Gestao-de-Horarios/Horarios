from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.decorators import require_auth, require_project
from src.core.errors import ClassNotFoundResponse
from src.core.schemas import SuccessResponse
from src.projects.projects_db.dao import ClassDAO, SessionDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.classes import (
    ClassDetailResponse,
    ClassesResponse,
    ClassStatsResponse,
)
from src.projects.views.schemas.week_blocks import WeekBlock


class ProjectClassesView(View):
    """API endpoint: list all classes in the project with stats."""

    @require_auth
    @require_project
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        with get_project_session(general_db(project_id)) as db_session:
            stats = ClassDAO(db_session).get_all_with_stats()
            result = [ClassStatsResponse.model_validate(s) for s in stats]

        return JsonResponse(
            SuccessResponse(
                message="Classes retrieved successfully",
                data=ClassesResponse(classes=result),
            ).model_dump(),
        )


class ProjectClassView(View):
    """API endpoint: retrieve a single class with its schedule blocks."""

    @require_auth
    @require_project
    def get(self, request: HttpRequest, project_id: int, class_id: UUID) -> HttpResponse:
        with get_project_session(general_db(project_id)) as db_session:
            class_ = ClassDAO(db_session).get(class_id)
            if class_ is None:
                return ClassNotFoundResponse()

            blocks = WeekBlock.from_sessions(
                SessionDAO(db_session).get_by_class(
                    class_id,
                    includes=list(SessionDAO.Include),
                ),
            )

            return JsonResponse(
                SuccessResponse(
                    message="Class retrieved successfully",
                    data=ClassDetailResponse.model_validate_with_extras(
                        class_,
                        extras={"blocks": blocks},
                    ),
                ).model_dump(),
            )
