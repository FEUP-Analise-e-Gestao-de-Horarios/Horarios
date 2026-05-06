from pydantic import BaseModel, computed_field

from src.core.mixins import ValidateWithExtrasMixin
from src.projects.views.schemas.shared import RedBlockBase, RoomBase
from src.projects.views.schemas.week_blocks import WeekBlock


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
    blocks: list[WeekBlock]
    red_blocks: list[RedBlockBase]
