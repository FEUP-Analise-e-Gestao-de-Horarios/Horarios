from uuid import UUID

from pydantic import BaseModel

from src.core.mixins import ValidateWithExtrasMixin
from src.projects.views.schemas.shared import RedBlockResponse, SessionResponse


class ProjectRoomsResponse(BaseModel):
    rooms: list[RoomStatsResponse]
    count: int


class RoomStatsResponse(BaseModel):
    id: UUID

    name: str
    type: str | None
    size: str | None
    seats: str | None

    sessions: int
    red_blocks: int


class RoomDetailResponse(ValidateWithExtrasMixin, BaseModel):
    id: UUID

    name: str
    type: str | None
    size: str | None
    seats: str | None

    sessions: list[SessionResponse]
    red_blocks: list[RedBlockResponse]
