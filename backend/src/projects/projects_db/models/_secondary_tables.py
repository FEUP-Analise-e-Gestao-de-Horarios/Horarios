from sqlalchemy import Column, ForeignKey, Table, UniqueConstraint, Uuid

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

sessions_classes_subject = Table(
    "sessions_classes_subject",
    Base.metadata,
    Column("session_id", Uuid(as_uuid=True), ForeignKey("sessions.id"), primary_key=True),
    Column("class_id", Uuid(as_uuid=True), ForeignKey("classes.id"), primary_key=True),
    Column("subject_id", Uuid(as_uuid=True), ForeignKey("subjects.id"), primary_key=True),
    UniqueConstraint("session_id", "class_id", name="uq_session_class"),
)
