from pydantic import BaseModel

from src.core.mixins import ValidateWithExtrasMixin
from src.projects.views.schemas.sessions import WeekBlockResponse
from src.projects.views.schemas.shared import (
    ClassBase,
    DegreeBase,
    SubjectBase,
    TeacherBase,
    YearBase,
)


# -- Subjects list -----------------------------------------------------
class SubjectsResponse(BaseModel):
    subjects: list[SubjectStatsResponse]
    count: int


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
    teachers: list[TeacherBase]
    blocks: list[WeekBlockResponse]


# -- Classes list ------------------------------------------------------
class ClassesResponse(BaseModel):
    classes: list[ClassStatsResponse]
    count: int


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
    blocks: list[WeekBlockResponse]
