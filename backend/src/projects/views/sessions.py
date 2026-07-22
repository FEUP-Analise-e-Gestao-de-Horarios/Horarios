from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View

from src.core.decorators import require_auth, require_project
from src.core.errors import (
    ClassNotFoundResponse,
    InvalidBodyResponse,
    RoomNotFoundResponse,
    SessionNotFoundResponse,
    SubjectNotFoundResponse,
    TeacherNotFoundResponse,
    YearNotFoundResponse,
)
from src.core.schemas import SuccessResponse
from src.core.validation import validate_query_params, validate_request_body
from src.projects.projects_db.dao import (
    ClassDAO,
    RoomDAO,
    SessionClassSubjectDAO,
    SessionDAO,
    SubjectDAO,
    TeacherDAO,
    YearDAO,
)
from src.projects.projects_db.models.session import Session as SessionRow
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.sessions import (
    SessionPatchRequest,
    SessionsQueryParams,
    SessionsResponse,
)
from src.projects.views.schemas.week_blocks import SessionDetails, WeekBlock


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
    """API endpoint: update a single session (contract C1)."""

    @require_auth
    @require_project
    def patch(self, request: HttpRequest, project_id: int, session_id: UUID) -> HttpResponse:
        validated, err = validate_request_body(SessionPatchRequest, request.body)
        if err is not None:
            return err
        assert validated is not None

        with get_project_session(general_db(project_id)) as db_session:
            session_dao = SessionDAO(db_session)
            target = session_dao.get(session_id)
            if target is None:
                return SessionNotFoundResponse(f"Session not found: {session_id}.")

            if validated.teacher_ids is not None:
                missing = TeacherDAO(db_session).find_missing(validated.teacher_ids)
                if missing:
                    return TeacherNotFoundResponse()

            if validated.room_ids is not None:
                missing_rooms = RoomDAO(db_session).find_missing(validated.room_ids)
                if missing_rooms:
                    return RoomNotFoundResponse()

            if validated.class_ids is not None:
                missing_classes = ClassDAO(db_session).find_missing(validated.class_ids)
                if missing_classes:
                    return ClassNotFoundResponse(
                        f"Classes not found: {', '.join(str(i) for i in missing_classes)}.",
                    )

            if validated.subject_ids is not None:
                if len(validated.subject_ids) > 1:
                    return InvalidBodyResponse(
                        "A session may only teach a single subject; got "
                        f"{len(validated.subject_ids)} subject_ids.",
                    )
                missing_subjects = SubjectDAO(db_session).find_missing(validated.subject_ids)
                if missing_subjects:
                    return SubjectNotFoundResponse(
                        f"Subjects not found: {', '.join(str(i) for i in missing_subjects)}.",
                    )

            scs_dao = SessionClassSubjectDAO(db_session)
            pairs: list[tuple[UUID, UUID]] | None = None
            if validated.class_ids is not None or validated.subject_ids is not None:
                resolved_classes = (
                    validated.class_ids
                    if validated.class_ids is not None
                    else [scs.class_id for scs in scs_dao.get_by_session(session_id)]
                )
                if validated.subject_ids is not None:
                    resolved_subject_id = (
                        validated.subject_ids[0] if validated.subject_ids else None
                    )
                else:
                    existing_subjects = scs_dao.distinct_subject_ids(session_id)
                    if len(existing_subjects) > 1:
                        return InvalidBodyResponse(
                            "Session currently teaches more than one subject; "
                            "specify subject_ids explicitly to change its classes.",
                        )
                    resolved_subject_id = next(iter(existing_subjects), None)

                if resolved_classes and resolved_subject_id is None:
                    return InvalidBodyResponse(
                        "subject_ids is required when class_ids is non-empty.",
                    )
                pairs = (
                    [(class_id, resolved_subject_id) for class_id in resolved_classes]
                    if resolved_subject_id is not None
                    else []
                )

            def apply(row: SessionRow) -> None:
                session_dao.update_fields(
                    row,
                    weekday=validated.weekday,
                    start_time=validated.start_time,
                    duration=validated.duration,
                )
                if validated.teacher_ids is not None:
                    session_dao.replace_teachers(row, validated.teacher_ids)
                if validated.room_ids is not None:
                    session_dao.replace_rooms(row, validated.room_ids)
                if pairs is not None:
                    scs_dao.replace_for_session(row.id, pairs)

            for row in session_dao.get_siblings_in_weeks(target, validated.weeks):
                apply(row)

            db_session.commit()

            return JsonResponse(
                SuccessResponse(
                    message="Session updated successfully",
                    data=SessionDetails.from_session(target),
                ).model_dump(),
            )
