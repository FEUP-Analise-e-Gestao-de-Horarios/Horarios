"""Request and response schemas for the parallel-blocks endpoints."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.projects.projects_db.schemas.weekday import WeekDay
from src.projects.views.schemas.shared import DegreeBase


# -- Create one parallel group (request) -------------------------------
class CreateParallelGroupRequest(BaseModel):
    candidate_group_id: UUID
    block_ids: list[UUID]


# -- Created parallel group (response) ---------------------------------
class CreatedParallelGroupResponse(BaseModel):
    group_id: UUID


# -- Confirmed parallel groups (response) ------------------------------
class ParallelGroupResponse(BaseModel):
    group_id: UUID
    block_ids: list[UUID]


# -- Candidate parallel groups (response) ------------------------------
class ParallelCandidateClass(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    year_id: UUID


class ParallelCandidateSession(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    type: str
    start_time: int
    duration: int


class ParallelCandidateNode(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    original_block_id: UUID
    confirmed_group_id: UUID | None
    first_week: date
    last_week: date
    session: ParallelCandidateSession
    classes: list[ParallelCandidateClass]


class ParallelCandidateYear(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    degree: DegreeBase


class ParallelCandidateSubject(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    acronym: str
    name: str
    years: list[ParallelCandidateYear]


class ParallelCandidateEdge(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    source: UUID
    target: UUID
    weeks: list[date]


class ParallelCandidateGroupResponse(BaseModel):
    """Wire format of one candidate group; see ``ParallelBlockCandidateGroup``."""

    model_config = ConfigDict(from_attributes=True)

    candidate_group_id: UUID
    weekday: WeekDay
    subject: ParallelCandidateSubject
    nodes: list[ParallelCandidateNode]
    edges: list[ParallelCandidateEdge]
