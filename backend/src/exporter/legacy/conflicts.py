from collections.abc import Callable, Hashable, Iterable, Mapping
from itertools import combinations
from typing import Any
from uuid import UUID

from src.projects.projects_db.models.session import Session


def room_conflicts(sessions: list[Session]) -> set[tuple[UUID, UUID]]:
    """Return pairs of sessions that overlap while sharing a room."""
    return _conflicts_by_resource(
        sessions,
        lambda session: (room.id for room in session.rooms),
    )


def teacher_conflicts(sessions: list[Session]) -> set[tuple[UUID, UUID]]:
    """Return pairs of sessions that overlap while sharing a teacher."""
    return _conflicts_by_resource(
        sessions,
        lambda session: (teacher.id for teacher in session.teachers),
    )


def class_conflicts(sessions: list[Session]) -> set[tuple[UUID, UUID]]:
    """Return pairs of sessions that overlap while sharing a class."""
    return _conflicts_by_resource(
        sessions,
        lambda session: (link.class_id for link in session.session_class_subjects),
    )


def sessions_overlap(session1: Session, session2: Session) -> bool:
    """Return whether two ORM sessions overlap in week, weekday, and time."""
    if session1.week != session2.week:
        return False

    if session1.weekday != session2.weekday:
        return False

    session1_start = _time_to_minutes(session1.start_time)
    session1_end = session1_start + session1.duration * 30
    session2_start = _time_to_minutes(session2.start_time)
    session2_end = session2_start + session2.duration * 30

    return session1_start < session2_end and session2_start < session1_end


def sessions_conflict(
    session1: Session | Mapping[str, Any],
    session2: Session | Mapping[str, Any],
) -> bool:
    """Return whether two ORM or dict session records overlap on any resource."""
    if not _sessions_overlap_data(session1, session2):
        return False

    return any(
        (
            _room_ids(session1) & _room_ids(session2),
            _teacher_ids(session1) & _teacher_ids(session2),
            _class_ids(session1) & _class_ids(session2),
        ),
    )


def _time_to_minutes(time_hhmm: int) -> int:
    """Convert an integer HHMM time into minutes after midnight."""
    hours, minutes = divmod(time_hhmm, 100)
    return hours * 60 + minutes


def _conflicts_by_resource(
    sessions: list[Session],
    get_resources: Callable[[Session], Iterable[Hashable]],
) -> set[tuple[UUID, UUID]]:
    """Group sessions by resource and collect overlapping session id pairs."""
    sessions_by_resource: dict[Hashable, list[Session]] = {}

    for session in sessions:
        for resource_id in get_resources(session):
            sessions_by_resource.setdefault(resource_id, []).append(session)

    conflicts: set[tuple[UUID, UUID]] = set()

    for resource_sessions in sessions_by_resource.values():
        for session1, session2 in combinations(resource_sessions, 2):
            if sessions_overlap(session1, session2):
                conflicts.add(tuple(sorted((session1.id, session2.id), key=str)))

    return conflicts


def serialize_conflicts(conflicts: set[tuple[UUID, UUID]]) -> list[dict[str, str]]:
    """Serialize conflict id pairs into the legacy comparator response shape."""
    return [
        {
            "session1": str(session1_id),
            "session2": str(session2_id),
        }
        for session1_id, session2_id in conflicts
    ]


def _sessions_overlap_data(
    session1: Session | Mapping[str, Any],
    session2: Session | Mapping[str, Any],
) -> bool:
    """Return whether ORM or dict session records overlap in time coordinates."""
    if _normalize_scalar(_get_session_value(session1, "week")) != _normalize_scalar(
        _get_session_value(session2, "week"),
    ):
        return False

    if _normalize_scalar(_get_session_value(session1, "weekday")) != _normalize_scalar(
        _get_session_value(session2, "weekday"),
    ):
        return False

    session1_start = _time_to_minutes(int(_get_session_value(session1, "start_time")))
    session1_end = session1_start + int(_get_session_value(session1, "duration")) * 30
    session2_start = _time_to_minutes(int(_get_session_value(session2, "start_time")))
    session2_end = session2_start + int(_get_session_value(session2, "duration")) * 30

    return session1_start < session2_end and session2_start < session1_end


def _room_ids(session: Session | Mapping[str, Any]) -> set[str]:
    """Extract room ids from an ORM session or serialized session mapping."""
    if isinstance(session, Mapping):
        return {str(room_id) for room_id in session.get("room_ids", [])}

    return {str(room.id) for room in session.rooms}


def _teacher_ids(session: Session | Mapping[str, Any]) -> set[str]:
    """Extract teacher ids from an ORM session or serialized session mapping."""
    if isinstance(session, Mapping):
        return {str(teacher_id) for teacher_id in session.get("teacher_ids", [])}

    return {str(teacher.id) for teacher in session.teachers}


def _class_ids(session: Session | Mapping[str, Any]) -> set[str]:
    """Extract class ids from an ORM session or serialized session mapping."""
    if isinstance(session, Mapping):
        class_subjects = session.get("class_subjects", {})
        if isinstance(class_subjects, Mapping):
            return {str(class_id) for class_id in class_subjects}
        return {str(class_id) for class_id in class_subjects}

    return {str(link.class_id) for link in session.session_class_subjects}


def _get_session_value(session: Session | Mapping[str, Any], key: str) -> Any:
    """Read a session field from either a mapping or ORM object."""
    if isinstance(session, Mapping):
        return session[key]
    return getattr(session, key)


def _normalize_scalar(value: Any) -> str:
    """Normalize enum/date/scalar values for equality checks across representations."""
    if hasattr(value, "isoformat"):
        return value.isoformat()

    return str(getattr(value, "value", value))
