from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.errors import (
    ClassNotFoundResponse,
    NotAuthenticatedResponse,
    ProjectNotFoundResponse,
    YearNotFoundResponse,
)
from src.core.schemas import SuccessResponse
from src.projects.models import Project
from src.projects.projects_db.dao import ClassDAO, SessionDAO, YearDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.sessions import WeekBlockResponse
from src.projects.views.schemas.subjects import (
    ClassDetailResponse,
    ClassesResponse,
    ClassStatsResponse,
)


class ProjectYearClassesView(View):
    """API endpoint: list classes with stats for a given year."""

    def get(self, request: HttpRequest, project_id: int, year_id: UUID) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        # -- Fetch project -----------------------------------------------------
        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        # -- Query classes with stats from project DB --------------------------
        with get_project_session(general_db(project_id)) as db_session:
            if YearDAO(db_session).get(year_id) is None:
                return YearNotFoundResponse()

            stats = ClassDAO(db_session).get_by_year_with_stats(year_id)
            result = [ClassStatsResponse.model_validate(s, from_attributes=True) for s in stats]

        return JsonResponse(
            SuccessResponse(
                message="Classes retrieved successfully",
                data=ClassesResponse(classes=result, count=len(result)),
            ).model_dump(),
        )


class ProjectClassView(View):
    """API endpoint: retrieve a single class with its schedule blocks."""

    def get(self, request: HttpRequest, project_id: int, class_id: UUID) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        # -- Fetch project -----------------------------------------------------
        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        # -- Fetch class with year, degree and schedule blocks ----------------
        with get_project_session(general_db(project_id)) as db_session:
            class_ = ClassDAO(db_session).get(class_id)
            if class_ is None:
                return ClassNotFoundResponse()

            blocks = WeekBlockResponse.from_sessions(
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
                        extras={"degree": class_.year.degree, "blocks": blocks},
                    ),
                ).model_dump(),
            )
