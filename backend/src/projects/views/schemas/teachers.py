from pydantic import BaseModel, computed_field

from src.core.mixins import ValidateWithExtrasMixin
from src.projects.views.schemas.sessions import WeekBlockResponse
from src.projects.views.schemas.shared import ClassBase, RedBlockBase, SubjectBase, TeacherBase


# -- Teachers list -----------------------------------------------------
class TeachersResponse(BaseModel):
    teachers: list[TeacherStatsResponse]

    @computed_field
    @property
    def count(self) -> int:
        return len(self.teachers)


class TeacherStatsResponse(TeacherBase):
    subjects: int
    classes: int
    sessions: int
    red_blocks: int


# -- Teacher detail ----------------------------------------------------
class TeacherDetailResponse(ValidateWithExtrasMixin, TeacherBase):
    subjects: list[SubjectBase]
    classes: list[ClassBase]
    blocks: list[WeekBlockResponse]
    red_blocks: list[RedBlockBase]
