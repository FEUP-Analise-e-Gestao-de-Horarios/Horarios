from pydantic import BaseModel, computed_field

from src.core.mixins import ValidateWithExtrasMixin
from src.projects.views.schemas.shared import SubjectBase, YearWithDegree
from src.projects.views.schemas.week_blocks import WeekBlock


# -- Subjects list -----------------------------------------------------
class SubjectsResponse(BaseModel):
    subjects: list[SubjectStatsResponse]

    @computed_field
    @property
    def count(self) -> int:
        return len(self.subjects)


class SubjectStatsResponse(SubjectBase):
    sessions: int


# -- Subject detail ----------------------------------------------------
class SubjectDetailResponse(ValidateWithExtrasMixin, SubjectBase):
    years: list[YearWithDegree]
    blocks: list[WeekBlock]
