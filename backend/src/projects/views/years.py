from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.decorators import require_auth, require_project
from src.core.errors import YearNotFoundResponse
from src.core.schemas import SuccessResponse
from src.projects.projects_db.dao import ClassDAO, SubjectDAO, YearDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.degrees import (
    YearDetailResponse,
    YearsResponse,
    YearStatsResponse,
)


class ProjectYearsView(View):
    """API endpoint: list all years in the project with stats."""

    @require_auth
    @require_project
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        with get_project_session(general_db(project_id)) as db_session:
            stats = YearDAO(db_session).get_all_with_stats()
            result = [YearStatsResponse.model_validate(s, from_attributes=True) for s in stats]

            return JsonResponse(
                SuccessResponse(
                    message="Years retrieved successfully",
                    data=YearsResponse(years=result),
                ).model_dump(),
            )


class ProjectYearView(View):
    """API endpoint: retrieve a single year with stats for its subjects and classes."""

    @require_auth
    @require_project
    def get(self, request: HttpRequest, project_id: int, year_id: UUID) -> HttpResponse:
        with get_project_session(general_db(project_id)) as db_session:
            year = YearDAO(db_session).get(year_id)
            if year is None:
                return YearNotFoundResponse()

            subjects = sorted(
                SubjectDAO(db_session).get_by_year_with_stats(year_id),
                key=lambda s: s.number,
            )
            classes = sorted(
                ClassDAO(db_session).get_by_year_with_stats(year_id),
                key=lambda c: c.code,
            )

            return JsonResponse(
                SuccessResponse(
                    message="Year retrieved successfully",
                    data=YearDetailResponse.model_validate_with_extras(
                        year,
                        extras={
                            "degree": year.degree,
                            "subjects": subjects,
                            "classes": classes,
                        },
                    ),
                ).model_dump(),
            )
