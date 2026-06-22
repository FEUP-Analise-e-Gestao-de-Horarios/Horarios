from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.projects.projects_db.schemas.weekday import WeekDay


class TeacherStats(BaseModel):
    id: UUID

    number: int
    acronym: str
    name: str

    subjects: int
    classes: int
    sessions: int
    red_blocks: int


class TeacherConflict(dict):
    teacher_id: UUID
    teacher_number: int
    teacher_acronym: str
    teacher_name: str

    week: datetime.date
    weeks: list[datetime.date]
    weekday: WeekDay
    start_time: int
    duration: int

    collisions: int
    session_ids: list[UUID]
    red_blocks: int
    subject_labels: list[str]
