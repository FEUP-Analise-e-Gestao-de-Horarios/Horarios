from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from src.projects.projects_db.schemas.weekday import WeekDay


class ClassStats(BaseModel):
    id: UUID
    year_id: UUID

    code: str
    shift: int

    sessions: int


class ClassConflict(dict):
    class_id: UUID
    class_code: str

    week: datetime.date
    weekday: WeekDay
    start_time: int
    duration: int

    collisions: int
    session_ids: list[UUID]
