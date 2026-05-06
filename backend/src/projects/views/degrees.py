from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View
from sqlalchemy import select

from src.core.decorators import require_auth, require_project
from src.core.errors import DegreeNotFoundResponse
from src.core.schemas import SuccessResponse
from src.projects.projects_db.dao import ClassDAO, DegreeDAO, SubjectDAO
from src.projects.projects_db.models import Year
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.degrees import (
    DegreeDetailResponse,
    DegreesResponse,
    DegreeStatsResponse,
    DegreeYearResponse,
)


class ProjectDegreesView(View):
    """API endpoint: list all degrees with stats for a project."""

    @require_auth
    @require_project
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        with get_project_session(general_db(project_id)) as db_session:
            stats = DegreeDAO(db_session).get_all_with_stats()
            result = [DegreeStatsResponse.model_validate(s, from_attributes=True) for s in stats]

            return JsonResponse(
                SuccessResponse(
                    message="Degrees retrieved successfully",
                    data=DegreesResponse(degrees=result),
                ).model_dump(),
            )


class ProjectDegreeView(View):
    """API endpoint: retrieve a single degree with stats."""

    @require_auth
    @require_project
    def get(self, request: HttpRequest, project_id: int, degree_id: UUID) -> HttpResponse:
        with get_project_session(general_db(project_id)) as db_session:
            degree = DegreeDAO(db_session).get(degree_id)
            if degree is None:
                return DegreeNotFoundResponse()

            years = list(
                db_session.scalars(
                    select(Year).where(Year.degree_id == degree_id).order_by(Year.number),
                ),
            )

            subject_dao = SubjectDAO(db_session)
            class_dao = ClassDAO(db_session)

            year_details = [
                DegreeYearResponse.model_validate_with_extras(
                    year,
                    extras={
                        "subjects": sorted(
                            subject_dao.get_by_year_with_stats(year.id),
                            key=lambda s: s.number,
                        ),
                        "classes": sorted(
                            class_dao.get_by_year_with_stats(year.id),
                            key=lambda c: c.code,
                        ),
                    },
                )
                for year in years
            ]

            return JsonResponse(
                SuccessResponse(
                    message="Degree retrieved successfully",
                    data=DegreeDetailResponse.model_validate_with_extras(
                        degree,
                        extras={"years": year_details},
                    ),
                ).model_dump(),
            )
