import datetime
from collections.abc import Iterable, Sequence
from enum import Enum, auto
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.interfaces import LoaderOption

from src.projects.projects_db.dao.base_dao import BaseDAO
from src.projects.projects_db.models._secondary_tables import (
    session_rooms,
    session_teachers,
)
from src.projects.projects_db.models.class_ import Class
from src.projects.projects_db.models.room import Room
from src.projects.projects_db.models.session import Session
from src.projects.projects_db.models.session_class_subject import SessionClassSubject
from src.projects.projects_db.models.subject import Subject
from src.projects.projects_db.models.teacher import Teacher
from src.projects.projects_db.schemas.weekday import WeekDay


class SessionDAO(BaseDAO[Session]):
    """Data access object for Session records."""

    class Include(Enum):
        """Optional relationships to eager-load on Session query methods."""

        TEACHERS = auto()
        ROOMS = auto()
        SUBJECTS = auto()
        CLASSES = auto()

    def __init__(self, session: DBSession) -> None:
        super().__init__(Session, session)

    # -------------------------------------------------------------------
    # -- Create
    # -------------------------------------------------------------------

    def create(
        self,
        *,
        week: datetime.date,
        weekday: WeekDay,
        start_time: int,
        duration: int,
        type: str,
        original_block_id: UUID,
    ) -> Session:
        """Create and persist a new session row.

        Used by a session split (a class detached from a shared session
        becomes its own recurring slot, one row per week in scope, sharing a
        freshly generated `original_block_id`) — never by ingestion, which
        writes rows directly.
        """
        return self._create(
            week=week,
            weekday=weekday,
            start_time=start_time,
            duration=duration,
            type=type,
            original_block_id=original_block_id,
        )

    @classmethod
    def _load_options(cls, includes: Iterable[Include]) -> list[LoaderOption]:
        """Translate a collection of :class:`Include` flags into SQLAlchemy load options."""
        options: list[LoaderOption] = []
        for inc in includes:
            match inc:
                case cls.Include.TEACHERS:
                    options.append(selectinload(Session.teachers))
                case cls.Include.ROOMS:
                    options.append(selectinload(Session.rooms))
                case cls.Include.SUBJECTS:
                    options.append(
                        selectinload(Session.session_class_subjects).joinedload(
                            SessionClassSubject.subject,
                        ),
                    )
                case cls.Include.CLASSES:
                    options.append(
                        selectinload(Session.session_class_subjects).joinedload(
                            SessionClassSubject.class_,
                        ),
                    )
        return options

    # -------------------------------------------------------------------
    # -- Get Sessions
    # -------------------------------------------------------------------

    def get_by_teacher(
        self,
        teacher_id: UUID,
        includes: Iterable[Include] = (),
    ) -> list[Session]:
        """Return all sessions taught by the given teacher.

        Args:
            teacher_id: UUID of the teacher to filter by.
            includes: Relationships to eager-load on each returned Session.
                Defaults to no eager loading.

        Returns:
            List of Session instances, in an unspecified order.
        """
        return list(
            self.session.scalars(
                select(Session)
                .join(session_teachers, session_teachers.c.session_id == Session.id)
                .where(session_teachers.c.teacher_id == teacher_id)
                .options(*self._load_options(includes)),
            ).all(),
        )

    def get_by_subject(
        self,
        subject_id: UUID,
        includes: Iterable[Include] = (),
    ) -> list[Session]:
        """Return all sessions that teach the given subject.

        Args:
            subject_id: UUID of the subject to filter by.
            includes: Relationships to eager-load on each returned Session.
                Defaults to no eager loading.

        Returns:
            List of Session instances, in an unspecified order.
        """
        return list(
            self.session.scalars(
                select(Session)
                .join(SessionClassSubject, SessionClassSubject.session_id == Session.id)
                .where(SessionClassSubject.subject_id == subject_id)
                .distinct()
                .options(*self._load_options(includes)),
            ).all(),
        )

    def get_by_class(
        self,
        class_id: UUID,
        includes: Iterable[Include] = (),
    ) -> list[Session]:
        """Return all sessions attended by the given class.

        Args:
            class_id: UUID of the class to filter by.
            includes: Relationships to eager-load on each returned Session.
                Defaults to no eager loading.

        Returns:
            List of Session instances, in an unspecified order.
        """
        return list(
            self.session.scalars(
                select(Session)
                .join(SessionClassSubject, SessionClassSubject.session_id == Session.id)
                .where(SessionClassSubject.class_id == class_id)
                .distinct()
                .options(*self._load_options(includes)),
            ).all(),
        )

    def get_by_room(
        self,
        room_id: UUID,
        includes: Iterable[Include] = (),
        weeks: Sequence[datetime.date] | None = None,
    ) -> list[Session]:
        """Return all sessions that take place in the given room.

        Args:
            room_id: UUID of the room to filter by.
            includes: Relationships to eager-load on each returned Session.
                Defaults to no eager loading.
            weeks: If given, only sessions in these weeks are returned.

        Returns:
            List of Session instances, in an unspecified order.
        """
        stmt = (
            select(Session)
            .join(session_rooms, session_rooms.c.session_id == Session.id)
            .where(session_rooms.c.room_id == room_id)
            .options(*self._load_options(includes))
        )
        if weeks is not None:
            stmt = stmt.where(Session.week.in_(weeks))
        return list(self.session.scalars(stmt).all())

    def get_by_year(
        self,
        year_id: UUID,
        includes: Iterable[Include] = (),
        weeks: Sequence[datetime.date] | None = None,
        subject_ids: Sequence[UUID] = (),
        class_ids: Sequence[UUID] = (),
        weekdays: Sequence[WeekDay] = (),
    ) -> list[Session]:
        """Return all sessions for any subject in the given year.

        Args:
            year_id: UUID of the year to filter by.
            includes: Relationships to eager-load on each returned Session.
                Defaults to no eager loading.
            weeks: If given, only sessions in these weeks are returned.
            subject_ids: If non-empty, restrict to sessions teaching any of
                these subjects.
            class_ids: If non-empty, restrict to sessions attended by any of
                these classes.
            weekdays: If non-empty, restrict to sessions on any of these
                weekdays.

        Returns:
            List of Session instances, in an unspecified order.
        """
        stmt = (
            select(Session)
            .join(SessionClassSubject, SessionClassSubject.session_id == Session.id)
            .join(Class, Class.id == SessionClassSubject.class_id)
            .where(Class.year_id == year_id)
            .distinct()
            .options(*self._load_options(includes))
        )
        if weeks is not None:
            stmt = stmt.where(Session.week.in_(weeks))
        if subject_ids:
            stmt = stmt.where(SessionClassSubject.subject_id.in_(subject_ids))
        if class_ids:
            stmt = stmt.where(SessionClassSubject.class_id.in_(class_ids))
        if weekdays:
            stmt = stmt.where(Session.weekday.in_(weekdays))
        return list(self.session.scalars(stmt).all())

    def get_year_week_fingerprints(
        self,
        year_id: UUID,
        subject_ids: Sequence[UUID] = (),
        class_ids: Sequence[UUID] = (),
        weekdays: Sequence[WeekDay] = (),
    ) -> list[tuple[datetime.date, frozenset[object]]]:
        """Return one timetable fingerprint per week of sessions in the year.

        Two weeks with equal fingerprints have identical timetables (same
        sessions in terms of weekday/start/duration/type and the same
        teacher, room, subject and class id sets per session). Lightweight
        compared to :meth:`get_by_year`: a single SQLite query pulls
        per-session core columns and ``group_concat``-aggregated id lists,
        with no ORM hydration of related teacher, room, subject or class
        objects. Intended as a cheap first pass that lets callers identify
        block boundaries before eagerly loading only representative weeks.

        Filters mirror :meth:`get_by_year` so the qualifying session set
        stays consistent across the two-pass flow. Aggregated id lists in
        the fingerprint always reflect the session's full content, not the
        filtered subset.

        Returns:
            ``(week, fingerprint)`` pairs sorted by week.
        """
        year_session_ids = (
            select(Session.id)
            .join(SessionClassSubject, SessionClassSubject.session_id == Session.id)
            .join(Class, Class.id == SessionClassSubject.class_id)
            .where(Class.year_id == year_id)
        )
        if subject_ids:
            year_session_ids = year_session_ids.where(
                SessionClassSubject.subject_id.in_(subject_ids),
            )
        if class_ids:
            year_session_ids = year_session_ids.where(
                SessionClassSubject.class_id.in_(class_ids),
            )
        return self._week_fingerprints(year_session_ids, weekdays=weekdays)

    def get_by_room_week_fingerprints(
        self,
        room_id: UUID,
    ) -> list[tuple[datetime.date, frozenset[object]]]:
        """Return one timetable fingerprint per week of sessions in the room.

        Lightweight counterpart to :meth:`get_by_room` that mirrors
        :meth:`get_year_week_fingerprints` but filters by room. Used as a
        cheap first pass to identify week-block boundaries before
        eagerly loading only representative weeks.

        Returns:
            ``(week, fingerprint)`` pairs sorted by week.
        """
        room_session_ids = select(session_rooms.c.session_id).where(
            session_rooms.c.room_id == room_id,
        )
        return self._week_fingerprints(room_session_ids)

    def _week_fingerprints(
        self,
        session_ids: Select,
        weekdays: Sequence[WeekDay] = (),
    ) -> list[tuple[datetime.date, frozenset[object]]]:
        """Compute per-week fingerprints over a Session.id subquery.

        Args:
            session_ids: A select statement returning the ``Session.id``
                values to fingerprint.
            weekdays: If non-empty, restrict fingerprinted sessions to
                these weekdays.

        Returns:
            ``(week, fingerprint)`` pairs sorted by week.
        """
        teacher_ids_expr = (
            select(func.group_concat(session_teachers.c.teacher_id))
            .where(session_teachers.c.session_id == Session.id)
            .correlate(Session)
            .scalar_subquery()
        )
        room_ids_expr = (
            select(func.group_concat(session_rooms.c.room_id))
            .where(session_rooms.c.session_id == Session.id)
            .correlate(Session)
            .scalar_subquery()
        )
        subject_ids_expr = (
            select(func.group_concat(SessionClassSubject.subject_id.distinct()))
            .where(SessionClassSubject.session_id == Session.id)
            .correlate(Session)
            .scalar_subquery()
        )
        class_ids_expr = (
            select(func.group_concat(SessionClassSubject.class_id.distinct()))
            .where(SessionClassSubject.session_id == Session.id)
            .correlate(Session)
            .scalar_subquery()
        )

        stmt = select(
            Session.week,
            Session.weekday,
            Session.start_time,
            Session.duration,
            Session.type,
            teacher_ids_expr.label("teacher_ids"),
            room_ids_expr.label("room_ids"),
            subject_ids_expr.label("subject_ids"),
            class_ids_expr.label("class_ids"),
        ).where(Session.id.in_(session_ids))
        if weekdays:
            stmt = stmt.where(Session.weekday.in_(weekdays))
        rows = self.session.execute(stmt).all()

        by_week: dict[datetime.date, list[tuple[object, ...]]] = {}
        for r in rows:
            sig = (
                r.weekday,
                r.start_time,
                r.duration,
                r.type,
                tuple(sorted(r.teacher_ids.split(","))) if r.teacher_ids else (),
                tuple(sorted(r.room_ids.split(","))) if r.room_ids else (),
                tuple(sorted(r.subject_ids.split(","))) if r.subject_ids else (),
                tuple(sorted(r.class_ids.split(","))) if r.class_ids else (),
            )
            by_week.setdefault(r.week, []).append(sig)

        return [(week, frozenset(by_week[week])) for week in sorted(by_week)]

    def get_by_subject_type(
        self,
        subject: Subject,
        type_: str,
    ) -> Sequence[Session]:
        """Return all sessions for a given subject and session type.

        Args:
            subject: The Subject instance to filter by.
            type_: The session type to filter by (e.g. "T", "TP", "PL").

        Returns:
            A sequence of matching Session instances.
        """
        return self.session.scalars(
            select(Session)
            .join(SessionClassSubject, SessionClassSubject.session_id == Session.id)
            .where(
                SessionClassSubject.subject_id == subject.id,
                Session.type == type_,
            ),
        ).fetchall()

    # -------------------------------------------------------------------
    # -- Update (contract C1)
    # -------------------------------------------------------------------

    def update_fields(
        self,
        session_row: Session,
        *,
        weekday: WeekDay | None = None,
        start_time: int | None = None,
        duration: int | None = None,
    ) -> None:
        """Apply the given plain-column changes to `session_row` in place.

        `None` means "leave unchanged" (a PATCH sends only changed fields),
        not "clear the value" — every one of these columns is non-nullable.
        """
        if weekday is not None:
            session_row.weekday = weekday
        if start_time is not None:
            session_row.start_time = start_time
        if duration is not None:
            session_row.duration = duration

    def replace_teachers(self, session_row: Session, teacher_ids: Sequence[UUID]) -> None:
        """Replace `session_row.teachers` wholesale with the given ids."""
        session_row.teachers = list(
            self.session.scalars(select(Teacher).where(Teacher.id.in_(teacher_ids))).all(),
        )

    def replace_rooms(self, session_row: Session, room_ids: Sequence[UUID]) -> None:
        """Replace `session_row.rooms` wholesale with the given ids."""
        session_row.rooms = list(
            self.session.scalars(select(Room).where(Room.id.in_(room_ids))).all(),
        )

    def get_siblings_in_weeks(
        self,
        session_row: Session,
        weeks: Sequence[datetime.date],
    ) -> list[Session]:
        """Return every session sharing `session_row`'s `original_block_id`.

        Restricted to the given `weeks`, and always including `session_row`
        itself regardless of whether its own week is in `weeks` — a PATCH
        must never skip the session the client actually targeted. Used to
        fan an edit out across the weeks a recurring block is being edited
        for (see contract C1's `weeks` field).
        """
        if not weeks:
            return [session_row]
        siblings = self.session.scalars(
            select(Session).where(
                Session.original_block_id == session_row.original_block_id,
                Session.week.in_(weeks),
            ),
        ).all()
        by_id = {s.id: s for s in siblings}
        by_id[session_row.id] = session_row
        return list(by_id.values())

    # -------------------------------------------------------------------
    # -- Delete
    # -------------------------------------------------------------------

    def delete(self, session_row: Session) -> None:
        """Delete a session row.

        Used by a session merge (the reverse of a split): once a session's
        classes have all been moved elsewhere via
        `SessionClassSubjectDAO.remove_classes`, the now-empty row is
        deleted outright. Callers must clear `session_class_subjects` first
        — that relationship has no delete cascade configured, since nothing
        else in the app deletes a session with classes still attached.
        """
        self.session.delete(session_row)
