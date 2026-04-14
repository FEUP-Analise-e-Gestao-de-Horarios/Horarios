from pydantic import BaseModel

from src.core.mixins import ValidateWithExtrasMixin
from src.projects.views.schemas.sessions import WeekBlockResponse
from src.projects.views.schemas.shared import RedBlockBase, RoomBase


class ProjectRoomsResponse(BaseModel):
    rooms: list[RoomStatsResponse]
    count: int


class RoomStatsResponse(RoomBase):
    sessions: int
    red_blocks: int


class RoomDetailResponse(ValidateWithExtrasMixin, RoomBase):
    blocks: list[WeekBlockResponse]
    red_blocks: list[RedBlockBase]
