from uuid import UUID

from pydantic import BaseModel, ConfigDict

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
    count: int


class DegreeStatsResponse(DegreeBase):
    years: int
    subjects: int
    classes: int
    sessions: int


# -- Degree detail -----------------------------------------------------
class DegreeDetailResponse(ValidateWithExtrasMixin, DegreeBase):
    years: list[YearDetailResponse]


class YearDetailResponse(ValidateWithExtrasMixin, YearBase):
    subjects: list[SubjectWithSessions]
    classes: list[ClassWithSessions]


# -- Years list --------------------------------------------------------
class YearsResponse(BaseModel):
    years: list[YearStatsResponse]
    count: int


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
