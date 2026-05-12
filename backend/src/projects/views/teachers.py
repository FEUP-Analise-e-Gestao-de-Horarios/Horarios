from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.decorators import require_auth, require_project
from src.core.errors import TeacherNotFoundResponse
from src.core.schemas import SuccessResponse
from src.projects.projects_db.dao import ClassDAO, SessionDAO, SubjectDAO, TeacherDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.teachers import (
    TeacherDetailResponse,
    TeachersResponse,
    TeacherStatsResponse,
)
from src.projects.views.schemas.week_blocks import WeekBlock


class ProjectTeachersView(View):
    """API endpoint: list all teachers with stats for a project."""

    @require_auth
    @require_project
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        with get_project_session(general_db(project_id)) as db_session:
            stats = TeacherDAO(db_session).get_all_with_stats()
            result = [TeacherStatsResponse.model_validate(s) for s in stats]

            return JsonResponse(
                SuccessResponse(
                    message="Teachers retrieved successfully",
                    data=TeachersResponse(teachers=result),
                ).model_dump(),
            )


class ProjectTeacherView(View):
    """API endpoint: retrieve a single teacher with subjects, classes, and sessions."""

    @require_auth
    @require_project
    def get(self, request: HttpRequest, project_id: int, teacher_id: UUID) -> HttpResponse:
        with get_project_session(general_db(project_id)) as db_session:
            teacher = TeacherDAO(db_session).get(teacher_id)
            if teacher is None:
                return TeacherNotFoundResponse()

            subjects = SubjectDAO(db_session).get_by_teacher(teacher_id)
            classes = ClassDAO(db_session).get_by_teacher(teacher_id)
            blocks = WeekBlock.from_sessions(
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
