from uuid import UUID

from pydantic import BaseModel

from src.projects.projects_db.schemas.weekday import WeekDay
from src.projects.services.schemas.conflicts import ConflictResult


class ConflictsResponse(BaseModel):
    conflicts: list[ConflictResult]
    count: int


class UpdateConflictTagRequest(BaseModel):
    tags: list[str]


class ConflictPreviewRequest(BaseModel):
    original_block_id: UUID
    weekday: WeekDay
    start_time: int
    duration: int
    teacher_ids: list[UUID]
    room_ids: list[UUID]
    class_ids: list[UUID]


class ConflictPreviewResponse(BaseModel):
    solved: list[ConflictResult]
    new: list[ConflictResult]
