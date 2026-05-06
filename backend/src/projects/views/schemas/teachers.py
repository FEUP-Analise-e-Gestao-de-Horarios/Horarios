from pydantic import BaseModel, computed_field

from src.core.mixins import ValidateWithExtrasMixin
from src.projects.views.schemas.shared import ClassBase, RedBlockBase, SubjectBase, TeacherBase
from src.projects.views.schemas.week_blocks import WeekBlock


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
    blocks: list[WeekBlock]
    red_blocks: list[RedBlockBase]
