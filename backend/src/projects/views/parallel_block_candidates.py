from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.errors import (
    NotAuthenticatedResponse,
    ProjectNotFoundResponse,
)
from src.core.schemas import SuccessResponse
from src.projects.models import Project
from src.projects.projects_db.dao.parallel_block_candidate_dao import ParallelBlockCandidateDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.projects_db.schemas.parallel_candidates import ParallelBlockCandidateFilters


class ProjectParallelBlockCandidateView(View):
    """API endpoint: list parallel classes."""

    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        year_id = request.GET.get("year_id")
        degree_id = request.GET.get("degree_id")
        subject_id = request.GET.get("subject_id")
        class_id = request.GET.get("class_id")
        start_time = request.GET.get("start_time")

        filters = ParallelBlockCandidateFilters(
            year_id=UUID(year_id) if year_id else None,
            degree_id=UUID(degree_id) if degree_id else None,
            subject_id=UUID(subject_id) if subject_id else None,
            class_id=UUID(class_id) if class_id else None,
            start_time=start_time or None,
        )

        with get_project_session(general_db(project_id)) as db_session:
            parallel_block_candidate_dao = ParallelBlockCandidateDAO(db_session)

            result = parallel_block_candidate_dao.get_all_groups_with_info(filters)

            return JsonResponse(
                SuccessResponse(
                    message="Candidate parallel groups retrieved successfully",
                    data=[group.model_dump(mode="json") for group in result],
                ).model_dump(),
            )
