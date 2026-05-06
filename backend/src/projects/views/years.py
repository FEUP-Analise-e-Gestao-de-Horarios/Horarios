from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.core.errors import (
    DegreeNotFoundResponse,
    NotAuthenticatedResponse,
    ProjectNotFoundResponse,
    YearNotFoundResponse,
)
from src.core.schemas import SuccessResponse
from src.projects.models import Project
from src.projects.projects_db.dao import DegreeDAO, YearDAO
from src.projects.projects_db.models import Class, Session, SessionClassSubject
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.degrees import (
    YearDetailResponse,
    YearsResponse,
    YearStatsResponse,
)
from src.projects.views.schemas.sessions import WeekBlockResponse


class ProjectYearsView(View):
    """API endpoint: list years with stats for a given degree."""

    def get(self, request: HttpRequest, project_id: int, degree_id: UUID) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        # -- Fetch project -----------------------------------------------------
        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        # -- Query years with stats from project DB ----------------------------
        with get_project_session(general_db(project_id)) as db_session:
            if DegreeDAO(db_session).get(degree_id) is None:
                return DegreeNotFoundResponse()

            stats = YearDAO(db_session).get_by_degree_with_stats(degree_id)
            result = [YearStatsResponse.model_validate(s, from_attributes=True) for s in stats]

            return JsonResponse(
                SuccessResponse(
                    message="Years retrieved successfully",
                    data=YearsResponse(years=result, count=len(result)),
                ).model_dump(),
            )


class ProjectYearView(View):
    """API endpoint: retrieve a year detail with its full timetable as week blocks."""

    def get(
        self,
        request: HttpRequest,
        project_id: int,
        degree_id: UUID,
        year_id: UUID,
    ) -> HttpResponse:
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        with get_project_session(general_db(project_id)) as db_session:
            if DegreeDAO(db_session).get(degree_id) is None:
                return DegreeNotFoundResponse()

            year = YearDAO(db_session).get(year_id)
            if year is None or year.degree_id != degree_id:
                return YearNotFoundResponse()

            sessions = list(
                db_session.scalars(
                    select(Session)
                    .join(SessionClassSubject, SessionClassSubject.session_id == Session.id)
                    .join(Class, Class.id == SessionClassSubject.class_id)
                    .where(Class.year_id == year_id)
                    .distinct()
                    .options(
                        selectinload(Session.teachers),
                        selectinload(Session.rooms),
                        selectinload(Session.session_class_subjects).selectinload(
                            SessionClassSubject.subject,
                        ),
                        selectinload(Session.session_class_subjects).selectinload(
                            SessionClassSubject.class_,
                        ),
                    ),
                ).all(),
            )

            blocks = WeekBlockResponse.from_sessions(sessions)

            return JsonResponse(
                SuccessResponse(
                    message="Year retrieved successfully",
                    data=YearDetailResponse.model_validate_with_extras(
                        year,
                        extras={"blocks": blocks},
                    ),
                ).model_dump(),
            )
