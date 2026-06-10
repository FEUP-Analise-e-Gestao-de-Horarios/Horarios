from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.projects.projects_db.schemas.weekday import WeekDay


class ParallelBlockCandidateSession(BaseModel):
    original_block_id: UUID
    class_codes: list[str]
    session_type: str


class ParallelBlockCandidateDetailResponse(BaseModel):
    candidate_group_id: UUID
    sessions: list[ParallelBlockCandidateSession]
    subject_name: str
    session_start_time: int
    session_weekday: WeekDay
    session_duration: int
    session_week: date
    year: int
    degree_id: UUID
    degree_name: str
    degree_acronym: str

    model_config = ConfigDict(from_attributes=True)


class ParallelBlockCandidateFilters(BaseModel):
    year_id: UUID | None = None
    degree_id: UUID | None = None
    subject_id: UUID | None = None
