from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.errors import NotAuthenticatedResponse, ProjectNotFoundResponse
from src.core.schemas import SuccessResponse
from src.projects.models import Project
from src.projects.projects_db.dao.session_dao import SessionDAO
from src.projects.projects_db.paths import general_db, initial_db
from src.projects.projects_db.registry import get_session


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
        # with Comparator(project_id) as comp:
        #     data = comp.database_differences()
        #     data.update(comp.database_conflicts())

        #     return JsonResponse(
        #         SuccessResponse(
        #             message="Project export computed successfully",
        #             data=ProjectExportResponse.model_validate(data),
        #         ).model_dump(),
        #     )
        with get_session(general_db(project_id)) as session:
            session_dao = SessionDAO(session)

            alias = session_dao.attach_db(initial_db(project_id))
            data = session_dao.get_changes_only(alias)
            session_dao.detach_db(alias)

            return JsonResponse(
                SuccessResponse(
                    message="Project export computed successfully",
                    data=data,
                ).model_dump(),
            )
