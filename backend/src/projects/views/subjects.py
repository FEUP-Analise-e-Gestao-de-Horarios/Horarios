from http import HTTPStatus

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.errors import ApiError, ErrorResponse
from src.core.schemas import SuccessResponse
from src.projects.models import Project
from src.projects.projects_db.dao import ClassDAO, SubjectDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.schemas import (
    ClassStatsResponse,
    ProjectClassesResponse,
    ProjectSubjectsResponse,
    SubjectStatsResponse,
)


class ProjectSubjectsView(View):
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return ErrorResponse(
                status=HTTPStatus.UNAUTHORIZED,
                code=ApiError.AUTH_NOT_AUTHENTICATED,
                message="User is not authenticated.",
            )

        # -- Fetch project -----------------------------------------------------
        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ErrorResponse(
                status=HTTPStatus.NOT_FOUND,
                code=ApiError.PROJECTS_NOT_FOUND,
                message="Project not found.",
            )

        # -- Query subjects with stats from project DB -------------------------
        with get_project_session(general_db(project_id)) as db_session:
            stats = SubjectDAO(db_session).get_all_with_stats()
            result = [
                SubjectStatsResponse(
                    id=str(s.id),
                    number=s.number,
                    code=s.code,
                    acronym=s.acronym,
                    name=s.name,
                    year_id=str(s.year_id),
                    year_number=s.year_number,
                    degree_id=str(s.degree_id),
                    degree_acronym=s.degree_acronym,
                    degree_name=s.degree_name,
                    num_sessions=s.num_sessions,
                )
                for s in stats
            ]

        return JsonResponse(
            SuccessResponse(
                message="Subjects retrieved successfully",
                data=ProjectSubjectsResponse(subjects=result, count=len(result)),
            ).model_dump(),
        )


class ProjectClassesView(View):
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return ErrorResponse(
                status=HTTPStatus.UNAUTHORIZED,
                code=ApiError.AUTH_NOT_AUTHENTICATED,
                message="User is not authenticated.",
            )

        # -- Fetch project -----------------------------------------------------
        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ErrorResponse(
                status=HTTPStatus.NOT_FOUND,
                code=ApiError.PROJECTS_NOT_FOUND,
                message="Project not found.",
            )

        # -- Query classes with stats from project DB --------------------------
        with get_project_session(general_db(project_id)) as db_session:
            stats = ClassDAO(db_session).get_all_with_stats()
            result = [
                ClassStatsResponse(
                    id=str(s.id),
                    code=s.code,
                    shift=s.shift,
                    year_id=str(s.year_id),
                    year_number=s.year_number,
                    degree_id=str(s.degree_id),
                    degree_acronym=s.degree_acronym,
                    degree_name=s.degree_name,
                    num_sessions=s.num_sessions,
                )
                for s in stats
            ]

        return JsonResponse(
            SuccessResponse(
                message="Classes retrieved successfully",
                data=ProjectClassesResponse(classes=result, count=len(result)),
            ).model_dump(),
        )
