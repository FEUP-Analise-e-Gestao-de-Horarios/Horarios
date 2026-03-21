from uuid import UUID

from pydantic import BaseModel


class RoomStats(BaseModel):
    id: UUID
    name: str
    type: str | None
    size: str | None
    seats: str | None
    num_sessions: int
