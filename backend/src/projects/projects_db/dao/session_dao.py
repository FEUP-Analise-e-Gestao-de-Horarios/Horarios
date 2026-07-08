import datetime
from collections.abc import Iterable, Sequence
from enum import Enum, auto
from typing import Any, cast
from uuid import UUID

from sqlalchemy import Select, bindparam, func, inspect, select, text
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.interfaces import LoaderOption

from src.projects.projects_db.dao.base_dao import (
    AddedRemovedRecords,
    BaseDAO,
    ChangedRecords,
    DBAlias,
)
from src.projects.projects_db.dao.class_dao import ClassDAO
from src.projects.projects_db.dao.room_dao import RoomDAO
from src.projects.projects_db.dao.subject_dao import SubjectDAO
from src.projects.projects_db.dao.teacher_dao import TeacherDAO
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

    @classmethod
    def _with_related_data(cls, query: Select[tuple[Session]]) -> Select[tuple[Session]]:
        return query.options(*cls._load_options(cls.Include))

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
        type_: str,
        original_block_id: UUID,
        teacher_ids: set[UUID],
        room_ids: set[UUID],
    ) -> Session:
        """Create a new session with its many-to-many associations.

        Args:
            week: The date representing the week of the session.
            weekday: The day of the week the session takes place.
            start_time: The starting timeslot of the session.
            duration: The duration of the session in timeslot units.
            type_: The session type (e.g. "T", "TP", "PL").
            original_block_id: UUID of the originating timetable block.
            teacher_ids: UUIDs of teachers to associate with this session.
            room_ids: UUIDs of rooms to associate with this session.

        Returns:
            The newly created Session instance, flushed to the session.
        """
        session = self._create(
            week=week,
            weekday=weekday,
            start_time=start_time,
            duration=duration,
            type=type_,
            original_block_id=original_block_id,
        )

        if teacher_ids:
            self.session.execute(
                session_teachers.insert(),
                [{"session_id": session.id, "teacher_id": tid} for tid in teacher_ids],
            )

        if room_ids:
            self.session.execute(
                session_rooms.insert(),
                [{"session_id": session.id, "room_id": rid} for rid in room_ids],
            )

        return session

    # -------------------------------------------------------------------
    # -- Get Sessions
    # -------------------------------------------------------------------

    def get(self, session_id: UUID) -> Session | None:
        """Retrieve a single session by its primary key."""
        query = self._with_related_data(select(Session).where(Session.id == session_id))
        return self.session.scalars(query).one_or_none()

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

    def get_by_week_weekday_start_time_and_class(
        self,
        *,
        week: datetime.date,
        weekday: WeekDay,
        start_time: int,
        class_id: UUID,
    ) -> Session | None:
        """Find a session by its week, weekday, start time, and class.

        Args:
            week: The date representing the week of the session.
            weekday: The day of the week.
            start_time: The starting timeslot.
            class_id: UUID of the class to filter by.

        Returns:
            The matching Session instance, or None if not found.
        """
        query = (
            select(Session)
            .join(SessionClassSubject, SessionClassSubject.session_id == Session.id)
            .where(
                Session.week == week,
                Session.weekday == weekday,
                Session.start_time == start_time,
                SessionClassSubject.class_id == class_id,
            )
        )
        return self.session.scalars(query).first()

    def get_by_week_and_block(
        self,
        *,
        week: datetime.date,
        original_block_id: UUID,
    ) -> Session | None:
        """Find a session by its week and originating timetable block.

        Args:
            week: The date representing the week of the session.
            original_block_id: UUID of the originating timetable block.

        Returns:
            The matching Session instance, or None if not found.
        """
        query = select(Session).where(
            Session.week == week,
            Session.original_block_id == original_block_id,
        )
        return self.session.scalars(query).one_or_none()

    # -------------------------------------------------------------------
    # -- Get Others
    # -------------------------------------------------------------------

    def get_subjects(self, session_id: UUID) -> list[Subject]:
        """Return distinct subjects taught in the given session."""
        return list(
            self.session.scalars(
                select(Subject)
                .join(SessionClassSubject, SessionClassSubject.subject_id == Subject.id)
                .where(SessionClassSubject.session_id == session_id)
                .distinct(),
            ).all(),
        )

    def get_classes(self, session_id: UUID) -> list[Class]:
        """Return distinct classes that participate in the given session."""
        return list(
            self.session.scalars(
                select(Class)
                .join(SessionClassSubject, SessionClassSubject.class_id == Class.id)
                .where(SessionClassSubject.session_id == session_id)
                .distinct(),
            ).all(),
        )

    def get_all_for_diff(self) -> list[Session]:
        return list(
            self.session.scalars(
                select(Session).options(
                    selectinload(Session.rooms),
                    selectinload(Session.teachers),
                    selectinload(Session.session_class_subjects),
                ),
            ).all(),
        )

    def _serialize_columns(self, obj: Session) -> dict[str, Any]:
        mapper = inspect(self.model)
        return {
            attr.key: getattr(obj, attr.key) for attr in mapper.column_attrs if attr.key != "id"
        }

    def to_diff_snapshot(self, obj: Session) -> dict[str, Any]:
        data = self._serialize_columns(obj)
        data["room_ids"] = sorted(str(room.id) for room in obj.rooms)
        data["teacher_ids"] = sorted(str(teacher.id) for teacher in obj.teachers)
        data["class_subjects"] = {
            str(link.class_id): str(link.subject_id)
            for link in sorted(
                obj.session_class_subjects,
                key=lambda x: str(x.class_id),
            )
        }
        return data

    def get_diff_map(self) -> dict[str, dict[str, Any]]:
        return {str(obj.id): self.to_diff_snapshot(obj) for obj in self.get_all_for_diff()}

    @staticmethod
    def _empty_added_removed_records() -> AddedRemovedRecords:
        return {"added": [], "removed": []}

    def _get_common_session_id_strings(self, other_db_alias: DBAlias) -> set[str]:
        other_alias = self._validate_db_alias(other_db_alias)
        current_table = self._qualified_table_name("main", Session.__tablename__)
        other_table = self._qualified_table_name(other_alias, Session.__tablename__)

        query = text(
            f"""
            SELECT current_session.id
            FROM {current_table} AS current_session
            INNER JOIN {other_table} AS other_session
                ON current_session.id = other_session.id
            """,
        )
        return {
            str(session_id)
            for session_id in self.session.connection().execute(query).scalars().all()
        }

    @staticmethod
    def _normalize_related_key(value: Any) -> str:
        return str(value).replace("-", "")

    @classmethod
    def _get_related_records(
        cls,
        dao: BaseDAO[Any],
        ids: set[Any],
        serializer,
    ) -> dict[str, dict[str, Any]]:
        if not ids:
            return {}

        return {
            cls._normalize_related_key(model.id): serializer(model)
            for model in dao.get_multiple(list(ids))
        }

    def _merge_named_relation_changes(
        self,
        changes: ChangedRecords,
        session_key_lookup: dict[str, Any],
        common_session_ids: set[str],
        *,
        field_name: str,
        foreign_key_name: str,
        relation_changes: AddedRemovedRecords,
        records_by_id: dict[str, dict[str, Any]],
    ) -> None:
        for change_type, rows in relation_changes.items():
            for row in rows:
                if str(row["session_id"]) not in common_session_ids:
                    continue

                session_key = session_key_lookup.get(
                    str(row["session_id"]),
                    row["session_id"],
                )
                session_key_lookup.setdefault(str(session_key), session_key)
                session_changes = changes.setdefault(session_key, {})

                if field_name not in session_changes:
                    session_changes[field_name] = self._empty_added_removed_records()

                relation_bucket = cast(AddedRemovedRecords, session_changes[field_name])
                relation_id = row[foreign_key_name]
                relation_data = records_by_id.get(
                    self._normalize_related_key(relation_id),
                    {},
                )
                relation_bucket[change_type].append(
                    {
                        foreign_key_name: relation_id,
                        **relation_data,
                    },
                )

    def get_changes_only(self, other_db_alias: DBAlias) -> ChangedRecords:
        changes = BaseDAO.get_changes_only(self, other_db_alias)
        session_key_lookup = {str(session_id): session_id for session_id in changes}
        common_session_ids = self._get_common_session_id_strings(other_db_alias)

        room_changes = BaseDAO.get_added_removed_records(
            self,
            other_db_alias,
            ["*"],
            "session_rooms",
        )
        room_ids = {row["room_id"] for rows in room_changes.values() for row in rows}
        self._merge_named_relation_changes(
            changes,
            session_key_lookup,
            common_session_ids,
            field_name="rooms",
            foreign_key_name="room_id",
            relation_changes=room_changes,
            records_by_id=self._get_related_records(
                RoomDAO(self.session),
                room_ids,
                lambda room: {
                    "room_name": room.name,
                    "room_type": room.type,
                    "room_size": room.size,
                    "room_seats": room.seats,
                },
            ),
        )

        teacher_changes = BaseDAO.get_added_removed_records(
            self,
            other_db_alias,
            ["*"],
            "session_teachers",
        )
        teacher_ids = {row["teacher_id"] for rows in teacher_changes.values() for row in rows}
        self._merge_named_relation_changes(
            changes,
            session_key_lookup,
            common_session_ids,
            field_name="teachers",
            foreign_key_name="teacher_id",
            relation_changes=teacher_changes,
            records_by_id=self._get_related_records(
                TeacherDAO(self.session),
                teacher_ids,
                lambda teacher: {
                    "teacher_number": teacher.number,
                    "teacher_acronym": teacher.acronym,
                    "teacher_name": teacher.name,
                },
            ),
        )

        class_subject_changes = BaseDAO.get_added_removed_records(
            self,
            other_db_alias,
            ["*"],
            SessionClassSubject.__tablename__,
        )
        class_ids = {row["class_id"] for rows in class_subject_changes.values() for row in rows}
        subject_ids = {row["subject_id"] for rows in class_subject_changes.values() for row in rows}
        class_records = self._get_related_records(
            ClassDAO(self.session),
            class_ids,
            lambda class_: {
                "class_code": class_.code,
                "class_shift": class_.shift,
            },
        )
        subject_records = self._get_related_records(
            SubjectDAO(self.session),
            subject_ids,
            lambda subject: {
                "subject_number": subject.number,
                "subject_code": subject.code,
                "subject_acronym": subject.acronym,
                "subject_name": subject.name,
            },
        )

        # Keep class/subject pairs together so a subject swap for one class is not
        # misreported as an unrelated class change.
        for change_type, rows in class_subject_changes.items():
            for row in rows:
                if str(row["session_id"]) not in common_session_ids:
                    continue

                session_key = session_key_lookup.get(
                    str(row["session_id"]),
                    row["session_id"],
                )
                session_key_lookup.setdefault(str(session_key), session_key)
                session_changes = changes.setdefault(session_key, {})

                if "class_subjects" not in session_changes:
                    session_changes["class_subjects"] = self._empty_added_removed_records()

                relation_bucket = cast(
                    AddedRemovedRecords,
                    session_changes["class_subjects"],
                )
                class_id = row["class_id"]
                subject_id = row["subject_id"]
                relation_bucket[change_type].append(
                    {
                        "class_id": class_id,
                        **class_records.get(
                            self._normalize_related_key(class_id),
                            {},
                        ),
                        "subject_id": subject_id,
                        **subject_records.get(
                            self._normalize_related_key(subject_id),
                            {},
                        ),
                    },
                )

        return changes

    def get_added_removed_records(self, other_db_alias: DBAlias) -> AddedRemovedRecords:
        records = super().get_added_removed_records(
            other_db_alias,
            ["id"],
            self.model.__tablename__,
        )
        other_alias = self._validate_db_alias(other_db_alias)

        return {
            "added": self._get_export_session_records("main", records["added"]),
            "removed": self._get_export_session_records(other_alias, records["removed"]),
        }

    def _get_export_session_records(
        self,
        db_alias: str,
        records: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        session_ids = [str(record["id"]) for record in records]
        if not session_ids:
            return []

        sessions_table = self._qualified_table_name(db_alias, Session.__tablename__)
        session_rooms_table = self._qualified_table_name(db_alias, session_rooms.name)
        rooms_table = self._qualified_table_name(db_alias, Room.__tablename__)
        session_teachers_table = self._qualified_table_name(db_alias, session_teachers.name)
        teachers_table = self._qualified_table_name(db_alias, Teacher.__tablename__)
        class_subjects_table = self._qualified_table_name(
            db_alias,
            SessionClassSubject.__tablename__,
        )
        classes_table = self._qualified_table_name(db_alias, Class.__tablename__)
        subjects_table = self._qualified_table_name(db_alias, Subject.__tablename__)

        query = text(
            f"""
            SELECT
                s.id,
                s.original_block_id,
                s.week,
                s.weekday,
                s.start_time,
                s.duration,
                s.type,
                r.id AS room_id,
                r.name AS room_name,
                t.id AS teacher_id,
                t.number AS teacher_number,
                t.acronym AS teacher_acronym,
                t.name AS teacher_name,
                c.id AS class_id,
                c.code AS class_code,
                sub.id AS subject_id,
                sub.name AS subject_name,
                sub.acronym AS subject_acronym,
                sub.code AS subject_code
            FROM {sessions_table} s
            LEFT JOIN {session_rooms_table} sr ON sr.session_id = s.id
            LEFT JOIN {rooms_table} r ON r.id = sr.room_id
            LEFT JOIN {session_teachers_table} st ON st.session_id = s.id
            LEFT JOIN {teachers_table} t ON t.id = st.teacher_id
            LEFT JOIN {class_subjects_table} scs ON scs.session_id = s.id
            LEFT JOIN {classes_table} c ON c.id = scs.class_id
            LEFT JOIN {subjects_table} sub ON sub.id = scs.subject_id
            WHERE s.id IN :session_ids
            ORDER BY s.week, s.weekday, s.start_time, s.id, c.code, sub.code, r.name, t.acronym
            """,
        ).bindparams(bindparam("session_ids", expanding=True))
        rows = self.session.connection().execute(query, {"session_ids": session_ids}).mappings()
        by_id: dict[str, dict[str, Any]] = {}

        for row in rows:
            session_id = str(row["id"])
            session_record = by_id.setdefault(
                session_id,
                {
                    "id": session_id,
                    "original_block_id": row["original_block_id"],
                    "week": row["week"],
                    "weekday": self._export_weekday_value(row["weekday"]),
                    "start_time": row["start_time"],
                    "duration": row["duration"],
                    "type": row["type"],
                    "room_ids": [],
                    "rooms": [],
                    "teacher_ids": [],
                    "teachers": [],
                    "class_ids": [],
                    "classes": [],
                    "subject_ids": [],
                    "subjects": [],
                },
            )
            if row["room_id"] is not None:
                self._append_unique(session_record["room_ids"], str(row["room_id"]))
            self._append_unique(session_record["rooms"], row["room_name"])
            if row["teacher_number"] is not None:
                self._append_unique(session_record["teacher_ids"], str(row["teacher_id"]))
                self._append_unique(
                    session_record["teachers"],
                    {
                        "number": row["teacher_number"],
                        "acronym": row["teacher_acronym"],
                        "name": row["teacher_name"],
                    },
                )
            if row["class_id"] is not None:
                self._append_unique(session_record["class_ids"], str(row["class_id"]))
            self._append_unique(session_record["classes"], row["class_code"])
            if row["subject_code"] is not None:
                self._append_unique(session_record["subject_ids"], str(row["subject_id"]))
                self._append_unique(
                    session_record["subjects"],
                    {
                        "name": row["subject_name"],
                        "acronym": row["subject_acronym"],
                        "code": row["subject_code"],
                    },
                )

        return [by_id.get(session_id, {"id": session_id}) for session_id in session_ids]

    @staticmethod
    def _append_unique(items: list[Any], value: Any) -> None:
        if value is not None and value not in items:
            items.append(value)

    @staticmethod
    def _export_weekday_value(value: Any) -> str:
        return WeekDay(value).value
