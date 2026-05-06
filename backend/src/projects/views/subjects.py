from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.decorators import require_auth, require_project
from src.core.errors import SubjectNotFoundResponse, YearNotFoundResponse
from src.core.schemas import SuccessResponse
from src.projects.projects_db.dao import SessionDAO, SubjectDAO, YearDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.sessions import WeekBlockResponse
from src.projects.views.schemas.subjects import (
    SubjectDetailResponse,
    SubjectsResponse,
    SubjectStatsResponse,
)


class ProjectSubjectsView(View):
    """API endpoint: list all subjects in the project with stats."""

    @require_auth
    @require_project
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        with get_project_session(general_db(project_id)) as db_session:
            stats = SubjectDAO(db_session).get_all_with_stats()
            result = [SubjectStatsResponse.model_validate(s, from_attributes=True) for s in stats]

        return JsonResponse(
            SuccessResponse(
                message="Subjects retrieved successfully",
                data=SubjectsResponse(subjects=result),
            ).model_dump(),
        )


class ProjectYearSubjectsView(View):
    """API endpoint: list subjects with stats for a given year."""

    @require_auth
    @require_project
    def get(self, request: HttpRequest, project_id: int, year_id: UUID) -> HttpResponse:
        with get_project_session(general_db(project_id)) as db_session:
            if YearDAO(db_session).get(year_id) is None:
                return YearNotFoundResponse()

            stats = SubjectDAO(db_session).get_by_year_with_stats(year_id)
            result = [SubjectStatsResponse.model_validate(s, from_attributes=True) for s in stats]

        return JsonResponse(
            SuccessResponse(
                message="Subjects retrieved successfully",
                data=SubjectsResponse(subjects=result),
            ).model_dump(),
        )


class ProjectSubjectView(View):
    """API endpoint: retrieve a single subject with its schedule blocks."""

    @require_auth
    @require_project
    def get(self, request: HttpRequest, project_id: int, subject_id: UUID) -> HttpResponse:
        with get_project_session(general_db(project_id)) as db_session:
            subject = SubjectDAO(db_session).get(subject_id)
            if subject is None:
                return SubjectNotFoundResponse()

            blocks = WeekBlockResponse.from_sessions(
                SessionDAO(db_session).get_by_subject(
                    subject_id,
                    includes=list(SessionDAO.Include),
                ),
            )

            return JsonResponse(
                SuccessResponse(
                    message="Subject retrieved successfully",
                    data=SubjectDetailResponse.model_validate_with_extras(
                        subject,
                        extras={"degree": subject.year.degree, "blocks": blocks},
                    ),
                ).model_dump(),
            )
