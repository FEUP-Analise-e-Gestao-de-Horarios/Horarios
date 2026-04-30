"""Base Pydantic response schemas, one per project-DB entity.

Each ``*Base`` model mirrors the attributes of the corresponding DB table and
is meant to be inherited (or embedded) by the per-endpoint response schemas.
"""

import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.projects.projects_db.schemas.weekday import WeekDay


class RedBlockBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    hour: int
    weekday: WeekDay


class RoomBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    name: str
    type: str | None
    size: str | None
    seats: str | None


class TeacherBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    number: int
    acronym: str
    name: str


class DegreeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    acronym: str
    name: str


class YearBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    degree_id: UUID

    number: int


class SubjectBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    year_id: UUID

    number: int
    code: str
    acronym: str
    name: str


class ClassBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    year_id: UUID

    code: str
    shift: int


class SessionBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    original_block_id: UUID

    week: datetime.date
    weekday: WeekDay
    start_time: int
    duration: int

    type: str


class SubjectWithSessions(SubjectBase):
    """A subject enriched with its session count — nested inside year details."""

    sessions: int


class ClassWithSessions(ClassBase):
    """A class enriched with its session count — nested inside year details."""

    sessions: int
