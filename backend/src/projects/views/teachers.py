from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.errors import (
    NotAuthenticatedResponse,
    ProjectNotFoundResponse,
    TeacherNotFoundResponse,
)
from src.core.schemas import SuccessResponse
from src.projects.models import Project
from src.projects.projects_db.dao import ClassDAO, SessionDAO, SubjectDAO, TeacherDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.sessions import WeekBlockResponse
from src.projects.views.schemas.teachers import (
    TeacherDetailResponse,
    TeachersResponse,
    TeacherStatsResponse,
)


class ProjectTeachersView(View):
    """API endpoint: list all teachers with stats for a project."""

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
            result = [TeacherStatsResponse.model_validate(s, from_attributes=True) for s in stats]

            return JsonResponse(
                SuccessResponse(
                    message="Teachers retrieved successfully",
                    data=TeachersResponse(teachers=result, count=len(result)),
                ).model_dump(),
            )


class ProjectTeacherView(View):
    """API endpoint: retrieve a single teacher with subjects, classes, and sessions."""

    def get(self, request: HttpRequest, project_id: int, teacher_id: UUID) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        # -- Fetch project -----------------------------------------------------
        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        # -- Fetch teacher with subjects, classes and sessions -----------------
        with get_project_session(general_db(project_id)) as db_session:
            teacher = TeacherDAO(db_session).get(teacher_id)
            if teacher is None:
                return TeacherNotFoundResponse()

            subjects = SubjectDAO(db_session).get_by_teacher(teacher_id)
            classes = ClassDAO(db_session).get_by_teacher(teacher_id)
            blocks = WeekBlockResponse.from_sessions(
                SessionDAO(db_session).get_by_teacher(
                    teacher_id,
                    includes=list(SessionDAO.Include),
                ),
            )

            return JsonResponse(
                SuccessResponse(
                    message="Teacher retrieved successfully",
                    data=TeacherDetailResponse.model_validate_with_extras(
                        teacher,
                        extras={"subjects": subjects, "classes": classes, "blocks": blocks},
                    ),
                ).model_dump(),
            )
