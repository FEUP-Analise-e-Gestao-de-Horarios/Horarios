from itertools import combinations
from uuid import UUID

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views import View
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.core.errors import (
    DegreeNotFoundResponse,
    NotAuthenticatedResponse,
    ProjectNotFoundResponse,
    YearNotFoundResponse,
)
from src.core.schemas import SuccessResponse
from src.projects.models import Project
from src.projects.projects_db.dao import DegreeDAO, YearDAO
from src.projects.projects_db.models import Class, Session, SessionClassSubject
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session as get_project_session
from src.projects.views.schemas.conflicts import ConflictResponse, ConflictsResponse
from src.projects.views.schemas.sessions import WeekBlockResponse

DAY_LABELS = {
    "monday": "Segunda",
    "tuesday": "Terça",
    "wednesday": "Quarta",
    "thursday": "Quinta",
    "friday": "Sexta",
    "saturday": "Sábado",
}


def minutes_to_time(value: int) -> str:
    hours = value // 100
    minutes = value % 100
    return f"{hours:02d}:{minutes:02d}"


def hhmm_to_minutes(value: int) -> int:
    hours = value // 100
    minutes = value % 100
    return hours * 60 + minutes


def session_classes(session: Session) -> list[Class]:
    seen: dict[UUID, Class] = {}
    for session_class_subject in session.session_class_subjects:
        seen[session_class_subject.class_.id] = session_class_subject.class_
    return list(seen.values())


def session_subjects(session: Session) -> list[str]:
    seen: dict[UUID, str] = {}
    for session_class_subject in session.session_class_subjects:
        seen[session_class_subject.subject.id] = session_class_subject.subject.acronym
    return list(seen.values())


def session_display_name(session: Session) -> str:
    subjects = session_subjects(session)
    classes = ", ".join(class_.code for class_ in session_classes(session))
    subject = subjects[0] if subjects else session.type
    turma_suffix = f" [Turma: {classes}]" if classes else ""
    return f"Aula {subject} ({DAY_LABELS.get(session.weekday, session.weekday)} - {minutes_to_time(session.start_time)}{turma_suffix})"


def rendered_event_ids(session: Session) -> list[str]:
    classes = session_classes(session)
    if classes:
        return [f"{session.id}-{class_.code}" for class_ in classes]
    return [str(session.id)]


def conflict_event_ids(
    left: Session,
    right: Session,
    shared_class_ids: set[UUID],
    has_teacher_or_room_conflict: bool,
) -> list[str]:
    if has_teacher_or_room_conflict:
        return sorted({*rendered_event_ids(left), *rendered_event_ids(right)})

    left_classes = session_classes(left)
    right_classes = session_classes(right)
    left_ids = [
        f"{left.id}-{class_.code}" for class_ in left_classes if class_.id in shared_class_ids
    ] or rendered_event_ids(left)
    right_ids = [
        f"{right.id}-{class_.code}" for class_ in right_classes if class_.id in shared_class_ids
    ] or rendered_event_ids(right)
    return sorted({*left_ids, *right_ids})


def build_conflicts(sessions: list[Session]) -> list[ConflictResponse]:
    conflicts: list[ConflictResponse] = []
    seen: set[tuple[str, str, str, str, str]] = set()

    for left, right in combinations(sessions, 2):
        if left.weekday != right.weekday:
            continue

        left_start = hhmm_to_minutes(left.start_time)
        left_end = left_start + left.duration * 30
        right_start = hhmm_to_minutes(right.start_time)
        right_end = right_start + right.duration * 30
        if not (right_start < left_end and right_end > left_start):
            continue

        left_classes = session_classes(left)
        right_classes = session_classes(right)

        shared_teacher_ids = {teacher.id for teacher in left.teachers} & {
            teacher.id for teacher in right.teachers
        }
        shared_room_ids = {room.id for room in left.rooms} & {room.id for room in right.rooms}
        shared_class_ids = {class_.id for class_ in left_classes} & {
            class_.id for class_ in right_classes
        }

        if not shared_teacher_ids and not shared_room_ids and not shared_class_ids:
            continue

        conflict_reasons: list[str] = []
        conflict_reasons.extend(
            f"Docente {teacher.acronym} está ocupado"
            for teacher in left.teachers
            if teacher.id in shared_teacher_ids
        )
        conflict_reasons.extend(
            f"Sala {room.name} está ocupada" for room in left.rooms if room.id in shared_room_ids
        )
        conflict_reasons.extend(
            f"Turma {class_.code} está ocupada"
            for class_ in left_classes
            if class_.id in shared_class_ids
        )

        event_ids = conflict_event_ids(
            left,
            right,
            shared_class_ids,
            bool(shared_teacher_ids or shared_room_ids),
        )
        day = DAY_LABELS.get(left.weekday, left.weekday)
        time = minutes_to_time(left.start_time)
        turma = ", ".join(class_.code for class_ in left_classes) or ", ".join(
            class_.code for class_ in right_classes
        )
        conflict_key = ("|".join(event_ids), day, time, turma, "|".join(conflict_reasons))
        if conflict_key in seen:
            continue
        seen.add(conflict_key)

        conflicts.append(
            ConflictResponse(
                id=f"{left.id}-{right.id}",
                event_ids=event_ids,
                event_names=[session_display_name(left), session_display_name(right)],
                day=day,
                time=time,
                turma=turma,
                conflict_reasons=conflict_reasons,
            ),
        )

    conflicts.sort(
        key=lambda conflict: (
            ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"].index(conflict.day)
            if conflict.day in ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]
            else 99,
            conflict.time,
            conflict.turma,
        ),
    )
    return conflicts


class ProjectYearConflictsView(View):
    """API endpoint: retrieve conflicts for a given degree year."""

    def get(
        self,
        request: HttpRequest,
        project_id: int,
        degree_id: UUID,
        year_id: UUID,
    ) -> HttpResponse:
        if not request.user.is_authenticated:
            return NotAuthenticatedResponse()

        try:
            Project.objects.get(pk=project_id)
        except Project.DoesNotExist:
            return ProjectNotFoundResponse()

        with get_project_session(general_db(project_id)) as db_session:
            if DegreeDAO(db_session).get(degree_id) is None:
                return DegreeNotFoundResponse()

            year = YearDAO(db_session).get(year_id)
            if year is None or year.degree_id != degree_id:
                return YearNotFoundResponse()

            sessions = list(
                db_session.scalars(
                    select(Session)
                    .join(SessionClassSubject, SessionClassSubject.session_id == Session.id)
                    .join(Class, Class.id == SessionClassSubject.class_id)
                    .where(Class.year_id == year_id)
                    .distinct()
                    .options(
                        selectinload(Session.teachers),
                        selectinload(Session.rooms),
                        selectinload(Session.session_class_subjects).selectinload(
                            SessionClassSubject.subject,
                        ),
                        selectinload(Session.session_class_subjects).selectinload(
                            SessionClassSubject.class_,
                        ),
                    ),
                ).all(),
            )

            blocks = WeekBlockResponse.from_sessions(sessions)
            block_sessions = [session for block in blocks for session in block.sessions]
            conflicts = build_conflicts(block_sessions)

            return JsonResponse(
                SuccessResponse(
                    message="Year conflicts retrieved successfully",
                    data=ConflictsResponse(conflicts=conflicts, count=len(conflicts)),
                ).model_dump(),
            )
