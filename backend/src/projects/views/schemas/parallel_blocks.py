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


# -- Confirm a subject's candidates (request) --------------------------
class ConfirmSubjectRequest(BaseModel):
    subject_id: UUID
    # The candidate group ids the client currently shows for this subject. The
    # server aborts the confirmation if they no longer match the live set, so a
    # subject is never confirmed against a stale view of its candidates.
    candidate_group_ids: list[UUID]


# -- Confirm every candidate (request) ---------------------------------
class ConfirmAllRequest(BaseModel):
    # Every candidate group id the client currently shows, across all subjects.
    # The server aborts if this no longer matches the live set.
    candidate_group_ids: list[UUID]


# -- Confirmed candidate ids (response) --------------------------------
class ConfirmedCandidatesResponse(BaseModel):
    candidate_group_ids: list[UUID]


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
    number: int
    degree: DegreeBase


class ParallelCandidateSubject(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    acronym: str
    name: str
    confirmed: bool = False
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
