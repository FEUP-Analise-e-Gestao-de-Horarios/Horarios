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
from src.projects.projects_db.dao import DegreeDAO, SubjectDAO, YearDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.subjects import (
    ProjectSubjectsResponse,
    SubjectStatsResponse,
)


class ProjectSubjectsView(View):
    def get(
        self,
        request: HttpRequest,
        project_id: int,
        degree_id: UUID,
        year_id: UUID,
    ) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        # -- Fetch project -----------------------------------------------------
        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        # -- Query subjects with stats from project DB -------------------------
        with get_project_session(general_db(project_id)) as db_session:
            if DegreeDAO(db_session).get(degree_id) is None:
                return DegreeNotFoundResponse()

            year = YearDAO(db_session).get(year_id)
            if year is None or year.degree_id != degree_id:
                return YearNotFoundResponse()

            stats = SubjectDAO(db_session).get_by_year_with_stats(year_id)
            result = [SubjectStatsResponse.model_validate(s, from_attributes=True) for s in stats]

        return JsonResponse(
            SuccessResponse(
                message="Subjects retrieved successfully",
                data=ProjectSubjectsResponse(subjects=result, count=len(result)),
            ).model_dump(),
        )
