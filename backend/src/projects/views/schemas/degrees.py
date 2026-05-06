from pydantic import BaseModel, computed_field

from src.core.mixins import ValidateWithExtrasMixin
from src.projects.views.schemas.shared import DegreeBase, YearBase


# -- Degrees list ------------------------------------------------------
class DegreesResponse(BaseModel):
    degrees: list[DegreeStatsResponse]

    @computed_field
    @property
    def count(self) -> int:
        return len(self.degrees)


class DegreeStatsResponse(DegreeBase):
    years: int
    subjects: int
    classes: int
    sessions: int


# -- Degree detail -----------------------------------------------------
class DegreeDetailResponse(ValidateWithExtrasMixin, DegreeBase):
    years: list[DegreeYearResponse]


class DegreeYearResponse(YearBase):
    subjects: int
    classes: int
    sessions: int
