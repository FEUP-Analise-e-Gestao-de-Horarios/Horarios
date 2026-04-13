import datetime
from collections.abc import Sequence
from typing import Any, cast
from uuid import UUID

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import selectinload

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
from src.projects.projects_db.models.session import Session
from src.projects.projects_db.models.session_class_subject import SessionClassSubject
from src.projects.projects_db.models.subject import Subject
from src.projects.projects_db.schemas.weekday import WeekDay


class SessionDAO(BaseDAO[Session]):
    """Data access object for Session records."""

    def __init__(self, session: DBSession) -> None:
        super().__init__(Session, session)

    @staticmethod
    def _with_related_data(query):
        return query.options(
            selectinload(Session.rooms),
            selectinload(Session.teachers),
            selectinload(Session.session_class_subjects).selectinload(
                SessionClassSubject.class_,
            ),
            selectinload(Session.session_class_subjects).selectinload(
                SessionClassSubject.subject,
            ),
        )

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

    def get_by_teacher(self, teacher_id: UUID) -> list[Session]:
        """Return all sessions taught by the given teacher.

        Args:
            teacher_id: UUID of the teacher to filter by.

        Returns:
            List of Session instances, in an unspecified order.
        """
        query = self._with_related_data(
            select(Session)
            .join(session_teachers, session_teachers.c.session_id == Session.id)
            .where(session_teachers.c.teacher_id == teacher_id),
        )
        return list(
            self.session.scalars(query).all(),
        )

    def get_by_room(self, room_id: UUID) -> list[Session]:
        """Return all sessions that take place in the given room.

        Args:
            room_id: UUID of the room to filter by.

        Returns:
            List of Session instances, in an unspecified order.
        """
        query = self._with_related_data(
            select(Session)
            .join(session_rooms, session_rooms.c.session_id == Session.id)
            .where(session_rooms.c.room_id == room_id),
        )
        return list(
            self.session.scalars(query).all(),
        )

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
    def _get_related_labels(dao: BaseDAO[Any], ids: set[Any]) -> dict[str, str]:
        if not ids:
            return {}

        return {str(model.id).replace("-", ""): str(model) for model in dao.get_multiple(list(ids))}

    def _merge_named_relation_changes(
        self,
        changes: ChangedRecords,
        session_key_lookup: dict[str, Any],
        common_session_ids: set[str],
        *,
        field_name: str,
        relation_name: str,
        foreign_key_name: str,
        relation_changes: AddedRemovedRecords,
        labels_by_id: dict[str, str],
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
                relation_bucket[change_type].append(
                    {
                        foreign_key_name: relation_id,
                        relation_name: labels_by_id.get(
                            str(relation_id),
                            str(relation_id),
                        ),
                    },
                )
        print(labels_by_id)

    def get_changes_only(self, other_db_alias: DBAlias) -> ChangedRecords:
        changes = BaseDAO.get_changes_only(self, other_db_alias)
        session_key_lookup = {str(session_id): session_id for session_id in changes}
        common_session_ids = self._get_common_session_id_strings(other_db_alias)

        room_changes = BaseDAO.get_added_removed_records(
            self,
            other_db_alias,
            "session_rooms",
        )
        room_ids = {row["room_id"] for rows in room_changes.values() for row in rows}
        self._merge_named_relation_changes(
            changes,
            session_key_lookup,
            common_session_ids,
            field_name="rooms",
            relation_name="room",
            foreign_key_name="room_id",
            relation_changes=room_changes,
            labels_by_id=self._get_related_labels(RoomDAO(self.session), room_ids),
        )

        teacher_changes = BaseDAO.get_added_removed_records(
            self,
            other_db_alias,
            "session_teachers",
        )
        teacher_ids = {row["teacher_id"] for rows in teacher_changes.values() for row in rows}
        self._merge_named_relation_changes(
            changes,
            session_key_lookup,
            common_session_ids,
            field_name="teachers",
            relation_name="teacher",
            foreign_key_name="teacher_id",
            relation_changes=teacher_changes,
            labels_by_id=self._get_related_labels(
                TeacherDAO(self.session),
                teacher_ids,
            ),
        )

        class_subject_changes = BaseDAO.get_added_removed_records(
            self,
            other_db_alias,
            SessionClassSubject.__tablename__,
        )
        class_ids = {row["class_id"] for rows in class_subject_changes.values() for row in rows}
        subject_ids = {row["subject_id"] for rows in class_subject_changes.values() for row in rows}
        class_labels = self._get_related_labels(ClassDAO(self.session), class_ids)
        subject_labels = self._get_related_labels(SubjectDAO(self.session), subject_ids)

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
                        "class": class_labels.get(str(class_id), str(class_id)),
                        "subject_id": subject_id,
                        "subject": subject_labels.get(str(subject_id), str(subject_id)),
                    },
                )

        return changes
