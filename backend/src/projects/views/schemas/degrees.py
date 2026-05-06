from uuid import UUID

from pydantic import BaseModel, ConfigDict, computed_field

from src.core.mixins import ValidateWithExtrasMixin
from src.projects.views.schemas.shared import (
    ClassWithSessions,
    DegreeBase,
    SubjectWithSessions,
    YearBase,
)


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


# -- Year detail -------------------------------------------------------
class YearDetailResponse(ValidateWithExtrasMixin, YearBase):
    degree: DegreeBase
    subjects: list[SubjectWithSessions]
    classes: list[ClassWithSessions]


# -- Years list --------------------------------------------------------
class YearsResponse(BaseModel):
    years: list[YearStatsResponse]

    @computed_field
    @property
    def count(self) -> int:
        return len(self.years)


class YearStatsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    degree_id: UUID
    degree_acronym: str
    degree_name: str

    number: int

    subjects: int
    classes: int
    sessions: int
