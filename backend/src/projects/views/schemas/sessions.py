"""Response schemas for the Session entity."""

from uuid import UUID

from pydantic import BaseModel, Field

from src.projects.projects_db.schemas.weekday import WeekDay
from src.projects.views.schemas.week_blocks import WeekBlock


# -- Query params ------------------------------------------------------
class SessionsQueryParams(BaseModel):
    year_id: UUID
    subject_ids: list[UUID] = Field(default_factory=list)
    class_ids: list[UUID] = Field(default_factory=list)
    weekdays: list[WeekDay] = Field(default_factory=list)


# -- Sessions list -----------------------------------------------------
class SessionsResponse(BaseModel):
    blocks: list[WeekBlock]
