from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.core.mixins import ValidateWithExtrasMixin
from src.projects.views.schemas.shared import (
    ClassWithSessions,
    DegreeBase,
    SubjectWithSessions,
    YearBase,
)


class ProjectDegreesResponse(BaseModel):
    degrees: list[DegreeStatsResponse]
    count: int


class DegreeStatsResponse(DegreeBase):
    years: int
    subjects: int
    classes: int
    sessions: int


class YearDetailResponse(ValidateWithExtrasMixin, YearBase):
    subjects: list[SubjectWithSessions]
    classes: list[ClassWithSessions]


class DegreeDetailResponse(ValidateWithExtrasMixin, DegreeBase):
    years: list[YearDetailResponse]


class ProjectYearsResponse(BaseModel):
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
