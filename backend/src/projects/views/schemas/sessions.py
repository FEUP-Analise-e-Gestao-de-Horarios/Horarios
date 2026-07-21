"""Response schemas for the Session entity."""

import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.projects.projects_db.schemas.weekday import WeekDay
from src.projects.views.schemas.week_blocks import SessionDetails, WeekBlock


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


# -- Split ---------------------------------------------------------------
class SessionSplitRequest(BaseModel):
    """POST body for splitting classes off a session into a new one.

    `class_ids` must be a non-empty, *proper* subset of the target session's
    current classes — detaching all of them is a rename, not a split (use
    PATCH instead). The detached classes get their own new session, one row
    per week in `weeks` (same fan-out semantics as `SessionPatchRequest`;
    empty/omitted means just the target's own week), sharing a freshly
    generated `original_block_id` so the split-off slot is a proper
    recurring block in its own right. `teacher_ids`/`room_ids`/`subject_ids`
    default to the target's own current values when omitted.
    """

    class_ids: list[UUID] = Field(min_length=1)
    weekday: WeekDay
    start_time: int = Field(ge=0, le=2359)
    duration: int = Field(ge=1)
    teacher_ids: list[UUID] | None = None
    room_ids: list[UUID] | None = None
    subject_ids: list[UUID] | None = None
    weeks: list[datetime.date] = Field(default_factory=list)


class SessionSplitResponse(BaseModel):
    original: SessionDetails
    created: SessionDetails
