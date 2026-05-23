from http import HTTPStatus
from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.decorators import require_auth, require_project
from src.core.errors import (
    ClassNotFoundResponse,
    NotAuthenticatedResponse,
    ProjectNotFoundResponse,
    SessionNotFoundResponse,
    SubjectNotFoundResponse,
    YearNotFoundResponse,
)
from src.core.schemas import SuccessResponse
from src.core.validation import validate_query_params
from src.projects.models import Project
from src.projects.projects_db.dao import ClassDAO, SessionDAO, SubjectDAO, YearDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.sessions import SessionsQueryParams, SessionsResponse
from src.projects.views.schemas.week_blocks import WeekBlock


class ProjectSessionsView(View):
    """API endpoint: list session blocks for a project, filtered by year."""

    @require_auth
    @require_project
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        params, err = validate_query_params(SessionsQueryParams, request.GET)
        if err is not None:
            return err

        with get_project_session(general_db(project_id)) as db_session:
            if YearDAO(db_session).get(params.year_id) is None:
                return YearNotFoundResponse(f"Year not found: {params.year_id}.")

            missing_subjects = SubjectDAO(db_session).find_missing_in_year(
                params.year_id,
                params.subject_ids,
            )
            if missing_subjects:
                return SubjectNotFoundResponse(
                    "Subjects not found in year "
                    f"{params.year_id}: {', '.join(str(i) for i in missing_subjects)}.",
                )

            missing_classes = ClassDAO(db_session).find_missing_in_year(
                params.year_id,
                params.class_ids,
            )
            if missing_classes:
                return ClassNotFoundResponse(
                    "Classes not found in year "
                    f"{params.year_id}: {', '.join(str(i) for i in missing_classes)}.",
                )

            session_dao = SessionDAO(db_session)

            fingerprints = session_dao.get_year_week_fingerprints(
                params.year_id,
                subject_ids=params.subject_ids,
                class_ids=params.class_ids,
                weekdays=params.weekdays,
            )
            groups = WeekBlock.group_by_fingerprint(fingerprints)
            representative_weeks = [repr_week for _, repr_week in groups]

            representative_sessions = session_dao.get_by_year(
                params.year_id,
                includes=list(SessionDAO.Include),
                weeks=representative_weeks,
                subject_ids=params.subject_ids,
                class_ids=params.class_ids,
                weekdays=params.weekdays,
            )

            blocks = WeekBlock.from_groups(groups, representative_sessions)

            return JsonResponse(
                SuccessResponse(
                    message="Sessions retrieved successfully",
                    data=SessionsResponse(blocks=blocks),
                ).model_dump(),
            )


class ProjectSessionView(View):
    """API endpoint: delete a single session from a project."""

    def delete(
        self,
        request: HttpRequest,
        project_id: int,
        session_id: str,
    ) -> HttpResponse:
        # -- Check user auth ---------------------------------------------------
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        # -- Fetch project -----------------------------------------------------
        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        # -- Delete session from project DB -----------------------------------
        with get_project_session(general_db(project_id)) as db_session:
            deleted = SessionDAO(db_session).delete_by_id(UUID(session_id))
            if not deleted:
                return SessionNotFoundResponse()

            db_session.commit()

        return JsonResponse(
            {"message": "Session deleted successfully"},
            status=HTTPStatus.OK,
        )
