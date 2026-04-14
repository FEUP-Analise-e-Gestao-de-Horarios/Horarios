import datetime
from typing import TYPE_CHECKING, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.projects.projects_db.schemas.weekday import WeekDay

if TYPE_CHECKING:
    from src.projects.projects_db.models import Session


class RedBlockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hour: int
    weekday: WeekDay


class SubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    year_id: UUID

    number: int
    code: str
    acronym: str
    name: str


class ClassResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    year_id: UUID

    code: str
    shift: int


class TeacherRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    number: int
    acronym: str
    name: str


class RoomRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_block_id: UUID

    week: datetime.date
    weekday: WeekDay
    start_time: int
    duration: int

    type: str

    teachers: list[TeacherRef]
    subjects: list[SubjectResponse]
    classes: list[ClassResponse]
    rooms: list[RoomRef]

    @classmethod
    def from_session(cls, session: Session) -> Self:
        """Build a SessionResponse from an eagerly-loaded Session ORM instance.

        Deduplicates subjects and classes across the session's
        ``session_class_subjects`` rows, since the same subject or class may
        appear in more than one pairing.
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
                "teachers": list(session.teachers),
                "rooms": list(session.rooms),
                "subjects": list(seen_subjects.values()),
                "classes": list(seen_classes.values()),
            },
        )
