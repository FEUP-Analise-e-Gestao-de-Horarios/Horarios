import datetime
from uuid import UUID

from pydantic import BaseModel

from src.projects.projects_db.schemas.weekday import WeekDay


class RoomStats(BaseModel):
    id: UUID

    name: str
    type: str | None
    size: str | None
    seats: str | None

    sessions: int
    red_blocks: int


class RoomConflict(dict):
    room_id: UUID
    room_name: str

    week: datetime.date
    weeks: list[datetime.date]
    weekday: WeekDay
    start_time: int
    duration: int

    collisions: int
    session_ids: list[UUID]
    subject_labels: list[str]
