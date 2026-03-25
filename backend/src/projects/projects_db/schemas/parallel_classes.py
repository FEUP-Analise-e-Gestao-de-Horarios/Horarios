from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.projects.projects_db.schemas.weekday import WeekDay


class SessionInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    week: datetime.date
    weekday: WeekDay
    start_time: int
    duration: int
    type: str
    original_block_id: UUID


class ClassInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    shift: int


class ParallelClasses(BaseModel):
    session_id: UUID
    weekday: str
    start_time: int
    classes: list[str]


class SessionParallelClasses(BaseModel):
    session: SessionInfo
    classes: list[ClassInfo]
