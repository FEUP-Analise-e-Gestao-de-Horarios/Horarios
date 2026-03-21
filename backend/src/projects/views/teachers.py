from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.errors import NotAuthenticatedResponse, ProjectNotFoundResponse
from src.core.schemas import SuccessResponse
from src.projects.models import Project
from src.projects.projects_db.dao import TeacherDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.teachers import ProjectTeachersResponse, TeacherStatsResponse


class ProjectTeachersView(View):
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        # -- Fetch project -----------------------------------------------------
        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        # -- Query teachers with stats from project DB -------------------------
        with get_project_session(general_db(project_id)) as db_session:
            stats = TeacherDAO(db_session).get_all_with_stats()
            result = [
                TeacherStatsResponse(
                    id=str(s.id),
                    number=s.number,
                    acronym=s.acronym,
                    name=s.name,
                    num_sessions=s.num_sessions,
                )
                for s in stats
            ]

        return JsonResponse(
            SuccessResponse(
                message="Teachers retrieved successfully",
                data=ProjectTeachersResponse(teachers=result, count=len(result)),
            ).model_dump(),
        )
