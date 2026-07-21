import uuid
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
    SessionMergeRequest,
    SessionPatchRequest,
    SessionSplitRequest,
    SessionSplitResponse,
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


class ProjectSessionSplitView(View):
    """API endpoint: detach some of a session's classes into a new session."""

    @require_auth
    @require_project
    def post(self, request: HttpRequest, project_id: int, session_id: UUID) -> HttpResponse:
        validated, err = validate_request_body(SessionSplitRequest, request.body)
        if err is not None:
            return err
        assert validated is not None

        with get_project_session(general_db(project_id)) as db_session:
            session_dao = SessionDAO(db_session)
            target = session_dao.get(session_id)
            if target is None:
                return SessionNotFoundResponse(f"Session not found: {session_id}.")

            scs_dao = SessionClassSubjectDAO(db_session)
            target_links = scs_dao.get_by_session(session_id)
            current_class_ids = {link.class_id for link in target_links}
            split_ids = set(validated.class_ids)

            if not split_ids <= current_class_ids:
                return ClassNotFoundResponse(
                    "class_ids must be classes currently on this session; not on it: "
                    f"{', '.join(str(i) for i in split_ids - current_class_ids)}.",
                )
            if split_ids == current_class_ids:
                return InvalidBodyResponse(
                    "class_ids covers every class on this session — that's a move, "
                    "not a split; use PATCH instead.",
                )

            # The detached slot's own new session teaches new_class_ids when
            # given — unlike class_ids, these needn't be classes the target
            # session currently has, since this is how a detached slot gets
            # reassigned to a different class altogether.
            assigned_class_ids = (
                validated.new_class_ids if validated.new_class_ids is not None else list(split_ids)
            )
            if validated.new_class_ids is not None:
                missing_new_classes = ClassDAO(db_session).find_missing(assigned_class_ids)
                if missing_new_classes:
                    return ClassNotFoundResponse(
                        "new_class_ids not found: "
                        f"{', '.join(str(i) for i in missing_new_classes)}.",
                    )

            if validated.teacher_ids is not None:
                missing_teachers = TeacherDAO(db_session).find_missing(validated.teacher_ids)
                if missing_teachers:
                    return TeacherNotFoundResponse()
            if validated.room_ids is not None:
                missing_rooms = RoomDAO(db_session).find_missing(validated.room_ids)
                if missing_rooms:
                    return RoomNotFoundResponse()

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
                subject_id = validated.subject_ids[0] if validated.subject_ids else None
                if subject_id is None:
                    return InvalidBodyResponse("subject_ids is required.")
            else:
                # A session can in principle pair different classes with
                # different subjects, so the detached subject is resolved
                # from the classes actually being split off, not the
                # session as a whole.
                detached_subjects = {
                    link.subject_id for link in target_links if link.class_id in split_ids
                }
                if len(detached_subjects) != 1:
                    return InvalidBodyResponse(
                        "Could not infer a single subject for the detached classes; "
                        "specify subject_ids explicitly.",
                    )
                subject_id = next(iter(detached_subjects))

            teacher_ids = (
                validated.teacher_ids
                if validated.teacher_ids is not None
                else [t.id for t in target.teachers]
            )
            room_ids = (
                validated.room_ids
                if validated.room_ids is not None
                else [r.id for r in target.rooms]
            )
            new_pairs = [(class_id, subject_id) for class_id in assigned_class_ids]

            new_block_id = uuid.uuid7()
            created_by_week: dict[object, SessionRow] = {}
            for row in session_dao.get_siblings_in_weeks(target, validated.weeks):
                scs_dao.remove_classes(row.id, list(split_ids))
                new_row = session_dao.create(
                    week=row.week,
                    weekday=validated.weekday,
                    start_time=validated.start_time,
                    duration=validated.duration,
                    type=row.type,
                    original_block_id=new_block_id,
                )
                session_dao.replace_teachers(new_row, teacher_ids)
                session_dao.replace_rooms(new_row, room_ids)
                scs_dao.replace_for_session(new_row.id, new_pairs)
                created_by_week[row.week] = new_row

            db_session.commit()

            representative = created_by_week.get(target.week) or next(
                iter(created_by_week.values()),
            )

            return JsonResponse(
                SuccessResponse(
                    message="Session split successfully",
                    data=SessionSplitResponse(
                        original=SessionDetails.from_session(target),
                        created=SessionDetails.from_session(representative),
                    ),
                ).model_dump(),
            )


class ProjectSessionMergeView(View):
    """API endpoint: merge a session's classes into another, deleting it (reverse of split)."""

    @require_auth
    @require_project
    def post(self, request: HttpRequest, project_id: int, session_id: UUID) -> HttpResponse:
        validated, err = validate_request_body(SessionMergeRequest, request.body)
        if err is not None:
            return err
        assert validated is not None

        with get_project_session(general_db(project_id)) as db_session:
            session_dao = SessionDAO(db_session)
            source = session_dao.get(session_id)
            if source is None:
                return SessionNotFoundResponse(f"Session not found: {session_id}.")
            target = session_dao.get(validated.target_session_id)
            if target is None:
                return SessionNotFoundResponse(
                    f"Session not found: {validated.target_session_id}.",
                )
            if source.id == target.id:
                return InvalidBodyResponse("A session cannot be merged with itself.")

            if (source.weekday, source.start_time, source.duration, source.type) != (
                target.weekday,
                target.start_time,
                target.duration,
                target.type,
            ):
                return InvalidBodyResponse(
                    "Sessions must share the same weekday, start_time, duration and type to merge.",
                )
            if {t.id for t in source.teachers} != {t.id for t in target.teachers}:
                return InvalidBodyResponse("Sessions must have the same teachers to merge.")
            if {r.id for r in source.rooms} != {r.id for r in target.rooms}:
                return InvalidBodyResponse("Sessions must have the same rooms to merge.")

            scs_dao = SessionClassSubjectDAO(db_session)
            if scs_dao.distinct_subject_ids(source.id) != scs_dao.distinct_subject_ids(target.id):
                return InvalidBodyResponse("Sessions must teach the same subject to merge.")

            source_by_week = {
                row.week: row
                for row in session_dao.get_siblings_in_weeks(
                    source,
                    validated.weeks,
                )
            }
            target_by_week = {
                row.week: row
                for row in session_dao.get_siblings_in_weeks(
                    target,
                    validated.weeks,
                )
            }
            weeks_to_merge = sorted(source_by_week.keys() & target_by_week.keys())
            if not weeks_to_merge:
                return InvalidBodyResponse(
                    "Sessions don't share any week in scope — nothing to merge.",
                )

            # Validate before mutating anything, so a bad week never leaves a
            # partially-merged pair of sessions behind.
            for week in weeks_to_merge:
                source_row = source_by_week[week]
                target_row = target_by_week[week]
                source_classes = {link.class_id for link in scs_dao.get_by_session(source_row.id)}
                target_classes = {link.class_id for link in scs_dao.get_by_session(target_row.id)}
                if source_classes & target_classes:
                    return InvalidBodyResponse(
                        f"Sessions already share a class in week {week} — nothing to merge.",
                    )

            for week in weeks_to_merge:
                source_row = source_by_week[week]
                target_row = target_by_week[week]
                source_pairs = [
                    (link.class_id, link.subject_id)
                    for link in scs_dao.get_by_session(source_row.id)
                ]
                target_pairs = [
                    (link.class_id, link.subject_id)
                    for link in scs_dao.get_by_session(target_row.id)
                ]
                scs_dao.remove_classes(source_row.id, [class_id for class_id, _ in source_pairs])
                scs_dao.replace_for_session(target_row.id, target_pairs + source_pairs)
                session_dao.delete(source_row)

            db_session.commit()

            return JsonResponse(
                SuccessResponse(
                    message="Sessions merged successfully",
                    data=SessionDetails.from_session(target),
                ).model_dump(),
            )
