import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.projects.projects_db.schemas.weekday import WeekDay


class ConflictResult(BaseModel):
    id: str
    event_ids: list[str]
    event_names: list[str]
    day: str
    time: int
    turma: list[str]
    conflict_reasons: list[str]
    tag: str | None = None


class ConflictData(BaseModel):
    conflict_rows: list[dict] = Field(default_factory=list)
    session_rows: list[dict] = Field(default_factory=list)
    teacher_rows: list[dict] = Field(default_factory=list)
    room_rows: list[dict] = Field(default_factory=list)
    class_rows: list[dict] = Field(default_factory=list)


class SimulatedClassSubject(BaseModel):
    """Lightweight stand-in for SessionClassSubject used in conflict preview."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    class_id: UUID
    subject_id: UUID | None = None
    class_: object | None = None
    subject: object | None = None


class SimulatedSession(BaseModel):
    """Mimics a Session ORM object for the purpose of conflict detection.

    Only the fields accessed by _compute_conflict_rows and its helpers need
    to be populated — week, weekday, start_time, duration, type,
    original_block_id, id, teachers, rooms, and session_class_subjects.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: UUID
    week: datetime.date
    weekday: WeekDay
    start_time: int
    duration: int
    type: str
    original_block_id: UUID
    teachers: list = Field(default_factory=list)
    rooms: list = Field(default_factory=list)
    session_class_subjects: list = Field(default_factory=list)
