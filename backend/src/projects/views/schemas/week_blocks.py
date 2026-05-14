import datetime
from collections.abc import Iterable
from typing import TYPE_CHECKING, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.projects.projects_db.schemas.weekday import WeekDay
from src.projects.views.schemas.shared import ClassBase, RoomBase, SubjectBase, TeacherBase

if TYPE_CHECKING:
    from src.projects.projects_db.models import Session


# -- WeekBlock ---------------------------------------------------------
class WeekBlock(BaseModel):
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
    sessions: list[SessionDetails]

    @staticmethod
    def _week_fingerprint(sessions: Iterable[Session]) -> frozenset[object]:
        """Hashable fingerprint of a week's sessions, excluding the ``week`` field.

        Each session contributes a tuple of its non-week attributes plus the
        sorted id-sets of its teachers and rooms and the sorted set of its
        (class id, subject id) pairs. The pairs are fingerprinted together
        rather than as two independent sets so that sessions mapping distinct
        subjects to distinct classes cannot collide. Two weeks with the same
        frozenset of these tuples have identical timetables.
        """
        return frozenset(
            (
                s.weekday,
                s.start_time,
                s.duration,
                s.type,
                tuple(sorted(t.id for t in s.teachers)),
                tuple(sorted(r.id for r in s.rooms)),
                tuple(sorted((scs.class_id, scs.subject_id) for scs in s.session_class_subjects)),
            )
            for s in sessions
        )

    @staticmethod
    def group_by_fingerprint(
        fingerprints: Iterable[tuple[datetime.date, frozenset[object]]],
    ) -> list[tuple[list[datetime.date], datetime.date]]:
        """Collapse contiguous weeks with identical fingerprints into blocks.

        Args:
            fingerprints: ``(week, fingerprint)`` pairs in chronological order.

        Returns:
            For each block, a ``(weeks_in_block, representative_week)`` pair.
            The representative is the first week of its block.
        """
        groups: list[tuple[list[datetime.date], datetime.date]] = []
        prev_fp: frozenset[object] | None = None
        for week, fp in fingerprints:
            if fp == prev_fp and groups:
                groups[-1][0].append(week)
            else:
                groups.append(([week], week))
                prev_fp = fp
        return groups

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

        fingerprints = [(week, cls._week_fingerprint(by_week[week])) for week in sorted(by_week)]
        groups = cls.group_by_fingerprint(fingerprints)

        return cls._from_blocks((weeks, by_week[repr_week]) for weeks, repr_week in groups)

    @classmethod
    def from_groups(
        cls,
        groups: Iterable[tuple[list[datetime.date], datetime.date]],
        representative_sessions: Iterable[Session],
    ) -> list[Self]:
        """Build responses from groups and a flat list of representative sessions.

        Args:
            groups: ``(weeks_in_block, representative_week)`` pairs from
                :meth:`group_by_fingerprint`.
            representative_sessions: Sessions for every representative week
                across all groups, eagerly loaded with teachers, rooms, and
                ``session_class_subjects`` (with subject and class).

        Returns:
            One :class:`WeekBlock` per input group, preserving order.
        """
        by_week: dict[datetime.date, list[Session]] = {}
        for s in representative_sessions:
            by_week.setdefault(s.week, []).append(s)

        return cls._from_blocks((weeks, by_week.get(repr_week, [])) for weeks, repr_week in groups)

    @classmethod
    def _from_blocks(
        cls,
        blocks: Iterable[tuple[list[datetime.date], list[Session]]],
    ) -> list[Self]:
        return [
            cls(
                weeks=weeks,
                sessions=[SessionDetails.from_session(s) for s in representative],
            )
            for weeks, representative in blocks
        ]


# -- Session -----------------------------------------------------------
class SessionDetails(BaseModel):
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
