"""Response schemas for the Session entity."""

import datetime
from collections.abc import Iterable
from typing import TYPE_CHECKING, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.projects.projects_db.schemas.weekday import WeekDay
from src.projects.views.schemas.shared import (
    ClassBase,
    RoomBase,
    SubjectBase,
    TeacherBase,
)

if TYPE_CHECKING:
    from src.projects.projects_db.models import Session


# -- Week block --------------------------------------------------------
class WeekBlockResponse(BaseModel):
    """A contiguous run of weeks that share an identical timetable.

    Two weeks belong to the same block iff, ignoring the ``week`` field,
    every session in one week has an exact content match in the other —
    same weekday, start time, duration, type, teachers, rooms, subjects
    and classes. ``original_block_id`` is deliberately not part of the
    equivalence (sessions may be re-templated or edited while still
    representing the same recurring slot).

    ``sessions`` is the canonical week's session list — any week in the
    block would produce an equivalent render.
    """

    weeks: list[datetime.date]
    sessions: list[SessionResponse]

    @classmethod
    def from_sessions(cls, sessions: Iterable[Session]) -> list[Self]:
        """Group sessions into contiguous blocks of weeks with identical timetables.

        Args:
            sessions: Eagerly-loaded Session ORM instances (teachers, rooms,
                and ``session_class_subjects`` with their subject/class must
                be loaded). Order is not important.

        Returns:
            Blocks sorted chronologically. Weeks inside each block are
            also sorted.
        """
        by_week: dict[datetime.date, list[Session]] = {}
        for s in sessions:
            by_week.setdefault(s.week, []).append(s)

        if not by_week:
            return []

        groups: list[tuple[list[datetime.date], list[Session]]] = []
        prev_signature: frozenset[object] | None = None

        for week in sorted(by_week.keys()):
            week_sessions = by_week[week]
            signature = cls._week_signature(week_sessions)
            if signature == prev_signature and groups:
                groups[-1][0].append(week)
            else:
                groups.append(([week], week_sessions))
                prev_signature = signature

        return [
            cls(
                weeks=weeks,
                sessions=[SessionResponse.from_session(s) for s in representative],
            )
            for weeks, representative in groups
        ]

    @staticmethod
    def _week_signature(sessions: Iterable[Session]) -> frozenset[object]:
        """Hashable fingerprint of a week's sessions, excluding the ``week`` field.

        Each session contributes a tuple of its non-week attributes plus the
        sorted id-sets of its teachers, rooms, subjects and classes. Two weeks
        with the same frozenset of these tuples have identical timetables.
        """
        return frozenset(
            (
                s.weekday,
                s.start_time,
                s.duration,
                s.type,
                tuple(sorted(t.id for t in s.teachers)),
                tuple(sorted(r.id for r in s.rooms)),
                tuple(sorted({scs.subject_id for scs in s.session_class_subjects})),
                tuple(sorted({scs.class_id for scs in s.session_class_subjects})),
            )
            for s in sessions
        )


# -- Session -----------------------------------------------------------
class SessionResponse(BaseModel):
    """A session enriched with its full teacher, subject, class and room lists."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_block_id: UUID

    week: datetime.date
    weekday: WeekDay
    start_time: int
    duration: int

    type: str

    rooms: list[RoomBase]
    teachers: list[TeacherBase]
    subjects: list[SubjectBase]
    classes: list[ClassBase]

    @classmethod
    def from_session(cls, session: Session) -> Self:
        """Build a SessionResponse from an eagerly-loaded Session ORM instance.

        Deduplicates subjects and classes across the session's
        ``session_class_subjects`` rows, since the same subject may be taught
        to several classes in the same session.
        """
        seen_subjects: dict[UUID, object] = {}
        seen_classes: dict[UUID, object] = {}
        for scs in session.session_class_subjects:
            seen_subjects[scs.subject_id] = scs.subject
            seen_classes[scs.class_id] = scs.class_

        return cls.model_validate(
            {
                "id": session.id,
                "original_block_id": session.original_block_id,
                "week": session.week,
                "weekday": session.weekday,
                "start_time": session.start_time,
                "duration": session.duration,
                "type": session.type,
                "rooms": list(session.rooms),
                "teachers": list(session.teachers),
                "subjects": list(seen_subjects.values()),
                "classes": list(seen_classes.values()),
            },
        )
