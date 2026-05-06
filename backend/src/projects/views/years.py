from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.errors import (
    DegreeNotFoundResponse,
    NotAuthenticatedResponse,
    ProjectNotFoundResponse,
    YearNotFoundResponse,
)
from src.core.schemas import SuccessResponse
from src.projects.models import Project
from src.projects.projects_db.dao import ClassDAO, DegreeDAO, SubjectDAO, YearDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.degrees import (
    YearDetailResponse,
    YearsResponse,
    YearStatsResponse,
)


class ProjectYearsView(View):
    """API endpoint: list all years in the project with stats."""

    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
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
            stats = YearDAO(db_session).get_all_with_stats()
            result = [YearStatsResponse.model_validate(s, from_attributes=True) for s in stats]

            return JsonResponse(
                SuccessResponse(
                    message="Years retrieved successfully",
                    data=YearsResponse(years=result, count=len(result)),
                ).model_dump(),
            )


class ProjectYearView(View):
    """API endpoint: retrieve a single year with stats for its subjects and classes."""

    def get(self, request: HttpRequest, project_id: int, year_id: UUID) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        # -- Fetch project -----------------------------------------------------
        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        # -- Fetch year with nested subject / class stats ----------------------
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


class ProjectDegreeYearsView(View):
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
