"""Response schemas for the Session entity."""

import datetime
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


# -- Update (contract C1) -----------------------------------------------
class SessionPatchRequest(BaseModel):
    """PATCH body for a single session. Omitted fields are left unchanged.

    `weeks`, when given, fans the same change out to every session sharing
    the target's `original_block_id` whose `week` is in this list (plus the
    target itself) — moving a recurring class only for the weeks currently
    selected/filtered in the UI, rather than every week it has ever run.
    Omitted or empty means "just this one session".
    """

    weekday: WeekDay | None = None
    start_time: int | None = Field(default=None, ge=0, le=2359)
    duration: int | None = Field(default=None, ge=1)
    teacher_ids: list[UUID] | None = None
    room_ids: list[UUID] | None = None
    class_ids: list[UUID] | None = None
    subject_ids: list[UUID] | None = None
    weeks: list[datetime.date] = Field(default_factory=list)
