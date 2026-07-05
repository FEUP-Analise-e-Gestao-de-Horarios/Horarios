import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.projects.projects_db.schemas.weekday import WeekDay


class EventTarget(BaseModel):
    """Where to navigate to edit the aula (session) behind a conflict event."""

    degree: str
    year: int
    week: str
    block_id: str


class ConflictResult(BaseModel):
    id: str
    event_ids: list[str]
    event_names: list[str]
    event_targets: dict[str, EventTarget] = Field(default_factory=dict)
    day: str
    time: int
    turma: list[str]
    block_ids: list[str] = Field(default_factory=list)
    degrees: list[str] = Field(default_factory=list)
    subjects: list[str] = Field(default_factory=list)
    conflict_reasons: list[str]
    tags: list[str] = Field(default_factory=list)


class ConflictData(BaseModel):
    conflict_rows: list[dict] = Field(default_factory=list)
    session_rows: list[dict] = Field(default_factory=list)
    teacher_rows: list[dict] = Field(default_factory=list)
    room_rows: list[dict] = Field(default_factory=list)
    class_rows: list[dict] = Field(default_factory=list)
    redblock_conflict_ids: set[str] = Field(default_factory=set)


class RedBlocks(BaseModel):
    """Per-resource unavailability slots.

    Each mapping is ``resource_id -> {weekday -> {slot start times in HHMM}}``,
    where every slot start time marks a 30-minute window in which the resource
    is unavailable.
    """

    teacher: dict[UUID, dict[WeekDay, set[int]]] = Field(default_factory=dict)
    room: dict[UUID, dict[WeekDay, set[int]]] = Field(default_factory=dict)
    class_: dict[UUID, dict[WeekDay, set[int]]] = Field(default_factory=dict)


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
