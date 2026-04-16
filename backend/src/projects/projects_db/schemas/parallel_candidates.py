from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.projects.projects_db.schemas.weekday import WeekDay


class ParallelBlockCandidateDetailResponse(BaseModel):
    candidate_group_id: UUID
    original_block_ids: list[UUID]
    subject_name: str
    session_start_time: int
    session_weekday: WeekDay
    session_duration: int
    session_week: date
    class_codes: str | None = None
    year: int
    degree_id: str
    degree_acronym: str

    model_config = ConfigDict(from_attributes=True)


class ParallelBlockCandidateFilters(BaseModel):
    year_id: UUID | None = None
    degree_id: UUID | None = None
    subject_id: UUID | None = None
