from pydantic import BaseModel, computed_field

from src.core.mixins import ValidateWithExtrasMixin
from src.projects.views.schemas.sessions import WeekBlockResponse
from src.projects.views.schemas.shared import (
    ClassBase,
    DegreeBase,
    SubjectBase,
    YearBase,
)


# -- Years list --------------------------------------------------------
class YearsResponse(BaseModel):
    years: list[YearStatsResponse]

    @computed_field
    @property
    def count(self) -> int:
        return len(self.years)


class YearStatsResponse(YearBase):
    subjects: int
    classes: int
    sessions: int


# -- Year detail -------------------------------------------------------
class YearDetailResponse(ValidateWithExtrasMixin, YearBase):
    degree: DegreeBase
    subjects: list[SubjectWithSessions]
    classes: list[ClassWithSessions]
    blocks: list[WeekBlockResponse]


class SubjectWithSessions(SubjectBase):
    sessions: int


class ClassWithSessions(ClassBase):
    sessions: int
