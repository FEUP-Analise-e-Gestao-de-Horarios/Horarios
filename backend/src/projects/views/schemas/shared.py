import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.projects.projects_db.schemas.weekday import WeekDay


class RedBlockResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hour: int
    weekday: WeekDay


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_block_id: UUID

    week: datetime.date
    weekday: WeekDay
    start_time: int
    duration: int

    type: str
