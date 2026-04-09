import logging
import uuid
from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View
from pydantic import ValidationError

from src.core.errors import (
    ApiError,
    ErrorResponse,
    NotAuthenticatedResponse,
    ProjectNotFoundResponse,
)
from src.core.schemas import SuccessResponse
from src.projects.models import Project
from src.projects.projects_db.dao.class_dao import ClassDAO
from src.projects.projects_db.dao.degree_dao import DegreeDAO
from src.projects.projects_db.dao.session_class_subject_dao import SessionClassSubjectDAO
from src.projects.projects_db.dao.session_dao import SessionDAO
from src.projects.projects_db.dao.subject_dao import SubjectDAO
from src.projects.projects_db.dao.year_dao import YearDAO
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.parallel_classes import (
    DegreeListResponse,
    DegreeResponse,
    ParallelGroupRequest,
    SessionListResponse,
    SessionResponse,
    SubjectListResponse,
    SubjectResponse,
    YearListResponse,
    YearResponse,
)

logger = logging.getLogger(__name__)


class ProjectsParallelDegreeListView(View):
    def get(self, request: HttpRequest, project_id: int) -> HttpResponse:
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        with get_project_session(general_db(project_id)) as db_session:
            degrees = DegreeDAO(db_session).get_with_parallel_classes()

            data = [
                DegreeResponse.model_validate(degree, from_attributes=True).model_dump()
                for degree in degrees
            ]

            return JsonResponse(
                SuccessResponse(
                    message="Degrees with parallel classes retrieved successfully",
                    data=DegreeListResponse(
                        count=len(data),
                        degrees=data,
                    ),
                ).model_dump(),
            )


class ProjectsParallelYearListView(View):
    def get(self, request: HttpRequest, project_id: int, degree_id: UUID) -> HttpResponse:
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        with get_project_session(general_db(project_id)) as db_session:
            years = YearDAO(db_session).get_with_parallel_classes(degree_id=degree_id)

            data = [
                YearResponse.model_validate(year, from_attributes=True).model_dump()
                for year in years
            ]

            return JsonResponse(
                SuccessResponse(
                    message="Years with parallel classes retrieved successfully",
                    data=YearListResponse(
                        count=len(data),
                        years=data,
                    ),
                ).model_dump(),
            )


class ProjectsParallelSubjectListView(View):
    def get(self, request: HttpRequest, project_id: int, year_id: UUID) -> HttpResponse:
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        with get_project_session(general_db(project_id)) as db_session:
            subjects = SubjectDAO(db_session).get_with_parallel_classes(year_id=year_id)

            data = [
                SubjectResponse.model_validate(subject, from_attributes=True).model_dump()
                for subject in subjects
            ]

            return JsonResponse(
                SuccessResponse(
                    message="Subjects with parallel classes retrieved successfully",
                    data=SubjectListResponse(
                        count=len(data),
                        subjects=data,
                    ),
                ).model_dump(),
            )


class ProjectsParallelSessionListView(View):
    def get(self, request: HttpRequest, project_id: int, subject_id: UUID) -> HttpResponse:
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        with get_project_session(general_db(project_id)) as db_session:
            sessionClassSubjectDAO = SessionClassSubjectDAO(db_session)

            sessions_ids = sessionClassSubjectDAO.get_parallel_session_ids_by_subject(
                subject_id=subject_id,
            )
            classes = sessionClassSubjectDAO.get_classes_by_session_ids(sessions_ids)
            sessions = SessionDAO(db_session).get_by_ids(sessions_ids)

            classes_by_session = {item.session: item.classes for item in classes}

            # filters same session in different week
            seen_blocks = set()
            unique_sessions = []
            for session in sessions:
                if session.original_block_id not in seen_blocks:
                    seen_blocks.add(session.original_block_id)
                    unique_sessions.append(session)

            session_responses = [
                SessionResponse(
                    id=session.id,
                    week=session.week,
                    weekday=session.weekday,
                    start_time=session.start_time,
                    duration=session.duration,
                    type=session.type,
                    original_block_id=session.original_block_id,
                    classes=classes_by_session.get(session.id, []),
                )
                for session in unique_sessions
            ]

            return JsonResponse(
                SuccessResponse(
                    message="Sessions with Parallel classes retrieved successfully",
                    data=SessionListResponse(
                        count=len(session_responses),
                        sessions=session_responses,
                    ).model_dump(),
                ).model_dump(),
            )


class ProjectsParallelGroupView(View):
    def post(self, request: HttpRequest, project_id: int) -> HttpResponse:
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        try:
            project = Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        try:
            payload = ParallelGroupRequest.model_validate_json(request.body)

            print(f"Payload: {payload}")
            with get_project_session(general_db(project_id)) as db_session:
                classDAO = ClassDAO(db_session)
                for group in payload.groups:
                    group_class_uuid = uuid.uuid7()  # generate a new uuid for the parallel group
                    for class_id in group.classes:
                        result = classDAO.update_parallel_group(class_id, group_class_uuid)
                        print(f"Updated class {class_id} -> {result.parallel_group}")

                db_session.commit()

        except ValidationError as e:
            errors = e.errors(include_input=False, include_url=False)
            message = "; ".join(
                f"{'.'.join(str(location) for location in err['loc'])}: {err['msg']}"
                if err.get("loc")
                else err["msg"]
                for err in errors
            )
            return ErrorResponse(status=400, code=ApiError.INVALID_BODY, message=message)

        project.has_selected_aulas_em_paralelo = True
        project.save()

        return JsonResponse(
            SuccessResponse(
                message="Groups assigned to parallel classes successfully",
                data={"assigned": payload.count},
            ).model_dump(),
        )
