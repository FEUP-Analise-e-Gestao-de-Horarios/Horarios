"""Response schemas for the Session entity."""

from uuid import UUID

from pydantic import BaseModel

from src.projects.views.schemas.week_blocks import WeekBlock


# -- Query params ------------------------------------------------------
class SessionsQueryParams(BaseModel):
    year_id: UUID


# -- Sessions list -----------------------------------------------------
class SessionsResponse(BaseModel):
    blocks: list[WeekBlock]
