from pydantic import BaseModel, computed_field

from src.core.mixins import ValidateWithExtrasMixin
from src.projects.views.schemas.shared import ClassBase, RedBlockBase, YearBase
from src.projects.views.schemas.week_blocks import WeekBlock


# -- Classes list ------------------------------------------------------
class ClassesResponse(BaseModel):
    classes: list[ClassStatsResponse]

    @computed_field
    @property
    def count(self) -> int:
        return len(self.classes)


class ClassStatsResponse(ClassBase):
    sessions: int


# -- Class detail ------------------------------------------------------
class ClassDetailResponse(ValidateWithExtrasMixin, ClassBase):
    year: YearBase
    blocks: list[WeekBlock]
    red_blocks: list[RedBlockBase]
