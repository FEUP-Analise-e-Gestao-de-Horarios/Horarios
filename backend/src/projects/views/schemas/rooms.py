from pydantic import BaseModel


class RoomStatsResponse(BaseModel):
    id: str
    name: str
    type: str | None
    size: str | None
    seats: str | None
    num_sessions: int


class ProjectRoomsResponse(BaseModel):
    rooms: list[RoomStatsResponse]
    count: int
