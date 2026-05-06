from pydantic import BaseModel, computed_field

from src.core.mixins import ValidateWithExtrasMixin
from src.projects.views.schemas.sessions import WeekBlockResponse
from src.projects.views.schemas.shared import RedBlockBase, RoomBase


# -- Rooms list --------------------------------------------------------
class RoomsResponse(BaseModel):
    rooms: list[RoomStatsResponse]

    @computed_field
    @property
    def count(self) -> int:
        return len(self.rooms)


class RoomStatsResponse(RoomBase):
    sessions: int
    red_blocks: int


# -- Room detail -------------------------------------------------------
class RoomDetailResponse(ValidateWithExtrasMixin, RoomBase):
    blocks: list[WeekBlockResponse]
    red_blocks: list[RedBlockBase]
