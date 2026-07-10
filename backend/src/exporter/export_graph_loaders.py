from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.sql.roles import ColumnArgumentRole, FromClauseRole

from src.exporter.export_graph_types import (
    GraphPrimitive,
    ResourceNode,
    ResourceOccupancy,
    ResourceSpec,
    SessionId,
    SessionSnapshot,
    TimePlacement,
)
from src.exporter.export_graph_utils import (
    get_time_slots,
    normalize_id,
    parse_week_date,
    to_uuid,
)
from src.projects.projects_db.models._secondary_tables import session_rooms, session_teachers
from src.projects.projects_db.models.class_ import Class
from src.projects.projects_db.models.room import Room
from src.projects.projects_db.models.session import Session as SessionModel
from src.projects.projects_db.models.session_class_subject import SessionClassSubject
from src.projects.projects_db.models.subject import Subject
from src.projects.projects_db.models.teacher import Teacher


@dataclass(frozen=True)
class ResourceAssociation:
    """SQLAlchemy association metadata for one dependency resource kind."""

    selectable: FromClauseRole
    resource_column: ColumnArgumentRole
    session_column: ColumnArgumentRole


RESOURCE_ASSOCIATIONS = {
    "rooms": ResourceAssociation(
        selectable=session_rooms,
        resource_column=session_rooms.c.room_id,
        session_column=session_rooms.c.session_id,
    ),
    "teachers": ResourceAssociation(
        selectable=session_teachers,
        resource_column=session_teachers.c.teacher_id,
        session_column=session_teachers.c.session_id,
    ),
    "classes": ResourceAssociation(
        selectable=SessionClassSubject,
        resource_column=SessionClassSubject.class_id,
        session_column=SessionClassSubject.session_id,
    ),
}


class ExportGraphSnapshotLoader:
    """Load the session snapshots needed by exporter graph generation."""

    def __init__(self, session: DBSession) -> None:
        """Store the SQLAlchemy session used by snapshot queries."""
        self.session = session

    def load_sessions_by_id(self, session_ids: list[SessionId]) -> dict[SessionId, SessionSnapshot]:
        """Load exporter session snapshots for the given sessions using set queries."""
        ids = list({to_uuid(session_id) for session_id in session_ids})
        if not ids:
            return {}

        rows = self.session.execute(
            select(
                SessionModel.id,
                SessionModel.start_time,
                SessionModel.duration,
                SessionModel.weekday,
                SessionModel.week,
                SessionModel.original_block_id,
            ).where(SessionModel.id.in_(ids)),
        ).all()

        snapshots = {
            row.id: {
                "id": row.id,
                "start_time": row.start_time,
                "duration": row.duration,
                "weekday": row.weekday,
                "week": row.week,
                "original_block_id": row.original_block_id,
                "room_ids": (),
                "rooms": [],
                "teacher_ids": (),
                "teachers": (),
                "subjects": (),
                "class_ids": (),
                "classes": [],
            }
            for row in rows
        }
        if not snapshots:
            return {}

        snapshot_ids = tuple(snapshots)
        self.attach_room_snapshots(snapshots, snapshot_ids)
        self.attach_teacher_snapshots(snapshots, snapshot_ids)
        self.attach_class_subject_snapshots(snapshots, snapshot_ids)
        return snapshots

    def attach_room_snapshots(
        self,
        snapshots: dict[SessionId, SessionSnapshot],
        session_ids: tuple[SessionId, ...],
    ) -> None:
        """Attach normalized room ids and room names to loaded session snapshots."""
        rows = self.session.execute(
            select(
                session_rooms.c.session_id,
                Room.id,
                Room.name,
                Room.type,
                Room.size,
                Room.seats,
            )
            .join(Room, Room.id == session_rooms.c.room_id)
            .where(session_rooms.c.session_id.in_(session_ids))
            .order_by(session_rooms.c.session_id, Room.name, Room.id),
        ).all()

        room_ids_by_session: dict[SessionId, list[str]] = defaultdict(list)
        rooms_by_session: dict[SessionId, list[str]] = defaultdict(list)
        room_details_by_session: dict[SessionId, list[SessionSnapshot]] = defaultdict(list)
        for row in rows:
            room_id = normalize_id(row.id)
            room_ids_by_session[row.session_id].append(room_id)
            rooms_by_session[row.session_id].append(row.name)
            room_details_by_session[row.session_id].append(
                {
                    "room_id": room_id,
                    "room_name": row.name,
                    "room_type": row.type,
                    "room_size": row.size,
                    "room_seats": row.seats,
                },
            )

        for session_id, snapshot in snapshots.items():
            snapshot["room_ids"] = tuple(room_ids_by_session[session_id])
            snapshot["rooms"] = rooms_by_session[session_id]
            snapshot["room_details"] = tuple(room_details_by_session[session_id])

    def attach_teacher_snapshots(
        self,
        snapshots: dict[SessionId, SessionSnapshot],
        session_ids: tuple[SessionId, ...],
    ) -> None:
        """Attach normalized teacher ids and public teacher details to snapshots."""
        rows = self.session.execute(
            select(
                session_teachers.c.session_id,
                Teacher.id,
                Teacher.number,
                Teacher.name,
                Teacher.acronym,
            )
            .join(Teacher, Teacher.id == session_teachers.c.teacher_id)
            .where(session_teachers.c.session_id.in_(session_ids))
            .order_by(session_teachers.c.session_id, Teacher.number, Teacher.id),
        ).all()

        teacher_ids_by_session: dict[SessionId, list[str]] = defaultdict(list)
        teachers_by_session: dict[SessionId, list[SessionSnapshot]] = defaultdict(list)
        for row in rows:
            teacher_ids_by_session[row.session_id].append(normalize_id(row.id))
            teachers_by_session[row.session_id].append(
                {"number": row.number, "name": row.name, "acronym": row.acronym},
            )

        for session_id, snapshot in snapshots.items():
            snapshot["teacher_ids"] = tuple(teacher_ids_by_session[session_id])
            snapshot["teachers"] = tuple(teachers_by_session[session_id])

    def attach_class_subject_snapshots(
        self,
        snapshots: dict[SessionId, SessionSnapshot],
        session_ids: tuple[SessionId, ...],
    ) -> None:
        """Attach class ids, class codes, and subject details to session snapshots."""
        rows = self.session.execute(
            select(
                SessionClassSubject.session_id,
                Class.id.label("class_id"),
                Class.code.label("class_code"),
                Subject.name.label("subject_name"),
                Subject.acronym.label("subject_acronym"),
                Subject.code.label("subject_code"),
            )
            .join(Class, Class.id == SessionClassSubject.class_id)
            .join(Subject, Subject.id == SessionClassSubject.subject_id)
            .where(SessionClassSubject.session_id.in_(session_ids))
            .order_by(
                SessionClassSubject.session_id,
                Class.code,
                Subject.acronym,
                Subject.code,
            ),
        ).all()

        class_ids_by_session: dict[SessionId, set[str]] = defaultdict(set)
        classes_by_session: dict[SessionId, list[str]] = defaultdict(list)
        subjects_by_session: dict[SessionId, list[SessionSnapshot]] = defaultdict(list)
        seen_classes: dict[SessionId, set[str]] = defaultdict(set)
        seen_subjects: dict[SessionId, set[tuple[str, str | None, str]]] = defaultdict(set)

        for row in rows:
            normalized_class_id = normalize_id(row.class_id)
            class_ids_by_session[row.session_id].add(normalized_class_id)

            if row.class_code not in seen_classes[row.session_id]:
                classes_by_session[row.session_id].append(row.class_code)
                seen_classes[row.session_id].add(row.class_code)

            subject_key = (row.subject_name, row.subject_acronym, row.subject_code)
            if subject_key not in seen_subjects[row.session_id]:
                subjects_by_session[row.session_id].append(
                    {
                        "name": row.subject_name,
                        "acronym": row.subject_acronym,
                        "code": row.subject_code,
                    },
                )
                seen_subjects[row.session_id].add(subject_key)

        for session_id, snapshot in snapshots.items():
            snapshot["class_ids"] = tuple(sorted(class_ids_by_session[session_id]))
            snapshot["classes"] = classes_by_session[session_id]
            snapshot["subjects"] = tuple(subjects_by_session[session_id])

    def load_original_block_weeks(
        self,
        original_block_ids: set[GraphPrimitive],
    ) -> dict[str, list[GraphPrimitive]]:
        """Load all weeks belonging to the recurring blocks touched by changes."""
        ids = list({to_uuid(block_id) for block_id in original_block_ids})
        if not ids:
            return {}

        rows = self.session.execute(
            select(SessionModel.original_block_id, SessionModel.week)
            .where(SessionModel.original_block_id.in_(ids))
            .order_by(SessionModel.original_block_id, SessionModel.week),
        ).all()

        weeks_by_block: dict[str, list[GraphPrimitive]] = defaultdict(list)
        for row in rows:
            weeks_by_block[normalize_id(row.original_block_id)].append(row.week)
        return dict(weeks_by_block)


class ResourceOccupancyLoader:
    """Load scoped current timetable occupancy for exporter dependency graphs."""

    def __init__(self, session: DBSession) -> None:
        """Store the SQLAlchemy session used by occupancy queries."""
        self.session = session

    def load(self, spec: ResourceSpec, needed_nodes: set[ResourceNode]) -> ResourceOccupancy:
        """Load current session ids occupying the requested resource/time nodes."""
        if not needed_nodes:
            return {}

        association = self.association_for_spec(spec)
        resources = {to_uuid(node[0]) for node in needed_nodes}
        weeks = {parse_week_date(node[3]) or node[3] for node in needed_nodes}
        weekdays = {node[2] for node in needed_nodes}

        stmt = (
            select(
                association.resource_column.label("resource_id"),
                SessionModel.id.label("session_id"),
                SessionModel.week,
                SessionModel.weekday,
                SessionModel.start_time,
                SessionModel.duration,
            )
            .select_from(association.selectable)
            .join(SessionModel, SessionModel.id == association.session_column)
            .where(
                association.resource_column.in_(resources),
                SessionModel.week.in_(weeks),
                SessionModel.weekday.in_(weekdays),
            )
            .order_by(
                association.resource_column,
                SessionModel.week,
                SessionModel.weekday,
                SessionModel.start_time,
            )
        )

        occupancy: ResourceOccupancy = {node: [] for node in needed_nodes}
        for row in self.session.execute(stmt).all():
            placement = TimePlacement(
                time_slots=get_time_slots(row.start_time, row.duration),
                weekday=row.weekday,
                week=row.week,
            )
            for time_slot in placement.time_slots:
                node = placement.node(normalize_id(row.resource_id), time_slot)
                if node in occupancy:
                    occupancy[node].append(row.session_id)

        return occupancy

    @staticmethod
    def association_for_spec(spec: ResourceSpec) -> ResourceAssociation:
        """Return SQLAlchemy association metadata for a resource graph kind."""
        try:
            return RESOURCE_ASSOCIATIONS[spec.graph_name]
        except KeyError as exc:
            raise ValueError(f"Unknown resource graph: {spec.graph_name}") from exc
