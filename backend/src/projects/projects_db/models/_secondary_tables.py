from sqlalchemy import Column, ForeignKey, Table, Uuid

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
)
