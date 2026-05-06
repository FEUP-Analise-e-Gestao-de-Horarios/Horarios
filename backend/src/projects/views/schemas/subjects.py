from pydantic import BaseModel, computed_field

from src.core.mixins import ValidateWithExtrasMixin
from src.projects.views.schemas.shared import (
    ClassBase,
    DegreeBase,
    SubjectBase,
    YearBase,
)
from src.projects.views.schemas.week_blocks import WeekBlock


# -- Subjects list -----------------------------------------------------
class SubjectsResponse(BaseModel):
    subjects: list[SubjectStatsResponse]

    @computed_field
    @property
    def count(self) -> int:
        return len(self.subjects)


class SubjectStatsResponse(BaseModel):
    id: str

    degree_id: str
    degree_acronym: str
    degree_name: str

    year_id: str
    year_number: int

    number: int
    code: str
    acronym: str
    name: str

    sessions: int


# -- Subject detail ----------------------------------------------------
class SubjectDetailResponse(ValidateWithExtrasMixin, SubjectBase):
    year: YearBase
    degree: DegreeBase
    blocks: list[WeekBlock]


# -- Classes list ------------------------------------------------------
class ClassesResponse(BaseModel):
    classes: list[ClassStatsResponse]

    @computed_field
    @property
    def count(self) -> int:
        return len(self.classes)


class ClassStatsResponse(BaseModel):
    id: str

    code: str
    shift: int

    year_id: str
    year_number: int

    degree_id: str
    degree_acronym: str
    degree_name: str

    sessions: int


# -- Class detail ------------------------------------------------------
class ClassDetailResponse(ValidateWithExtrasMixin, ClassBase):
    year: YearBase
    degree: DegreeBase
    blocks: list[WeekBlock]
