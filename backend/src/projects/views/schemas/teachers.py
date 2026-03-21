from uuid import UUID

from pydantic import BaseModel

from src.core.mixins import ValidateWithExtrasMixin
from src.projects.views.schemas.shared import ClassResponse, SessionResponse, SubjectResponse


class ProjectTeachersResponse(BaseModel):
    teachers: list[TeacherStatsResponse]
    count: int


class TeacherStatsResponse(BaseModel):
    id: UUID

    number: int
    acronym: str
    name: str

    subjects: int
    classes: int
    sessions: int


class TeacherDetailResponse(ValidateWithExtrasMixin, BaseModel):
    id: UUID
    number: int
    acronym: str
    name: str

    subjects: list[SubjectResponse]
    classes: list[ClassResponse]
    sessions: list[SessionResponse]
