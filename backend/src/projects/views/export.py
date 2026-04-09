from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.errors import NotAuthenticatedResponse, ProjectNotFoundResponse
from src.core.schemas import SuccessResponse
from src.exporter.differences import Comparator
from src.projects.models import Project
from src.projects.views.schemas.export import ProjectExportResponse


class ProjectExportView(View):
    """API endpoint: compute the diff and conflicts between a project's
    initial and current databases."""

    def post(self, request: HttpRequest, project_id: int) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        # -- Fetch project -----------------------------------------------------
        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        # -- Compute differences and conflicts ---------------------------------
        with Comparator(project_id) as comp:
            data = comp.database_differences()
            data.update(comp.database_conflicts())

            return JsonResponse(
                SuccessResponse(
                    message="Project export computed successfully",
                    data=ProjectExportResponse.model_validate(data),
                ).model_dump(),
            )
