from collections.abc import Callable, Hashable, Iterable
from itertools import combinations
from uuid import UUID

from src.projects.projects_db.models.session import Session


def room_conflicts(sessions: list[Session]) -> set[tuple[UUID, UUID]]:
    return _conflicts_by_resource(
        sessions,
        lambda session: (room.id for room in session.rooms),
    )


def teacher_conflicts(sessions: list[Session]) -> set[tuple[UUID, UUID]]:
    return _conflicts_by_resource(
        sessions,
        lambda session: (teacher.id for teacher in session.teachers),
    )


def class_conflicts(sessions: list[Session]) -> set[tuple[UUID, UUID]]:
    return _conflicts_by_resource(
        sessions,
        lambda session: (link.class_id for link in session.session_class_subjects),
    )


def sessions_overlap(session1: Session, session2: Session) -> bool:
    if session1.week != session2.week:
        return False

    if session1.weekday != session2.weekday:
        return False

    session1_start = _time_to_minutes(session1.start_time)
    session1_end = session1_start + session1.duration * 30
    session2_start = _time_to_minutes(session2.start_time)
    session2_end = session2_start + session2.duration * 30

    return session1_start < session2_end and session2_start < session1_end


def _time_to_minutes(time_hhmm: int) -> int:
    hours, minutes = divmod(time_hhmm, 100)
    return hours * 60 + minutes


def _conflicts_by_resource(
    sessions: list[Session],
    get_resources: Callable[[Session], Iterable[Hashable]],
) -> set[tuple[UUID, UUID]]:
    sessions_by_resource: dict[Hashable, list[Session]] = {}

    for session in sessions:
        for resource_id in get_resources(session):
            sessions_by_resource.setdefault(resource_id, []).append(session)

    conflicts: set[tuple[UUID, UUID]] = set()

    for resource_sessions in sessions_by_resource.values():
        for session1, session2 in combinations(resource_sessions, 2):
            if sessions_overlap(session1, session2):
                conflicts.add(tuple({session1.id, session2.id}))

    return conflicts


def serialize_conflicts(conflicts: set[tuple[UUID, UUID]]) -> list[dict[str, str]]:
    return [
        {
            "session1": str(session1_id),
            "session2": str(session2_id),
        }
        for session1_id, session2_id in conflicts
    ]
