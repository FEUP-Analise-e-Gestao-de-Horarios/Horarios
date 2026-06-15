from sqlalchemy import Column, ForeignKey, Index, Table, Uuid

from src.projects.projects_db.base import Base

session_rooms = Table(
    "session_rooms",
    Base.metadata,
    Column(
        "session_id",
        Uuid(native_uuid=False),
        ForeignKey("sessions.id"),
        primary_key=True,
    ),
    Column(
        "room_id",
        Uuid(native_uuid=False),
        ForeignKey("rooms.id"),
        primary_key=True,
    ),
    Index("ix_session_rooms_room_id", "room_id"),
    Index("ix_session_rooms_room_session", "room_id", "session_id"),
)

session_teachers = Table(
    "session_teachers",
    Base.metadata,
    Column(
        "session_id",
        Uuid(native_uuid=False),
        ForeignKey("sessions.id"),
        primary_key=True,
    ),
    Column(
        "teacher_id",
        Uuid(native_uuid=False),
        ForeignKey("teachers.id"),
        primary_key=True,
    ),
    Index("ix_session_teachers_teacher_id", "teacher_id"),
    Index("ix_session_teachers_teacher_session", "teacher_id", "session_id"),
)
