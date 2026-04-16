from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View
from sqlalchemy import select

from src.core.errors import (
    DegreeNotFoundResponse,
    NotAuthenticatedResponse,
    ProjectNotFoundResponse,
)
from src.core.schemas import SuccessResponse
from src.projects.models import Project
from src.projects.projects_db.dao import ClassDAO, DegreeDAO, SubjectDAO
from src.projects.projects_db.models import Year
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.degrees import (
    DegreeDetailResponse,
    DegreesResponse,
    DegreeStatsResponse,
    YearDetailResponse,
)


class ProjectDegreesView(View):
    """API endpoint: list all degrees with stats for a project."""

    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        # -- Fetch project -----------------------------------------------------
        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        # -- Query degrees with stats from project DB --------------------------
        with get_project_session(general_db(project_id)) as db_session:
            stats = DegreeDAO(db_session).get_all_with_stats()
            result = [DegreeStatsResponse.model_validate(s, from_attributes=True) for s in stats]

            return JsonResponse(
                SuccessResponse(
                    message="Degrees retrieved successfully",
                    data=DegreesResponse(degrees=result, count=len(result)),
                ).model_dump(),
            )


class ProjectDegreeView(View):
    """API endpoint: retrieve a single degree with stats."""

    def get(self, request: HttpRequest, project_id: int, degree_id: UUID) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        # -- Fetch project -----------------------------------------------------
        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        # -- Fetch degree with nested year / subject / class detail ------------
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
                YearDetailResponse.model_validate_with_extras(
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
