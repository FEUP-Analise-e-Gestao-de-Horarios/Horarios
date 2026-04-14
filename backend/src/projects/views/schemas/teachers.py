from pydantic import BaseModel

from src.core.mixins import ValidateWithExtrasMixin
from src.projects.views.schemas.sessions import WeekBlockResponse
from src.projects.views.schemas.shared import ClassBase, SubjectBase, TeacherBase


class ProjectTeachersResponse(BaseModel):
    teachers: list[TeacherStatsResponse]
    count: int


class TeacherStatsResponse(TeacherBase):
    subjects: int
    classes: int
    sessions: int


class TeacherDetailResponse(ValidateWithExtrasMixin, TeacherBase):
    subjects: list[SubjectBase]
    classes: list[ClassBase]
    blocks: list[WeekBlockResponse]
