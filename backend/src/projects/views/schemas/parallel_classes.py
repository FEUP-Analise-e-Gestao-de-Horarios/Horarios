import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.projects.projects_db.schemas.weekday import WeekDay


class DegreeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    acronym: str
    name: str


class DegreeListResponse(BaseModel):
    count: int
    degrees: list[DegreeResponse]


class YearResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    number: int
    degree: DegreeResponse


class SubjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    number: int
    code: str
    acronym: str
    name: str
    year: YearResponse


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    week: datetime.date
    weekday: WeekDay
    start_time: int
    duration: int
    type: str
    original_block_id: UUID


class ClassResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    shift: int


class NonTheoreticalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: UUID
    class_id: UUID
    subject_id: UUID
    session: SessionResponse
    class_: ClassResponse
    subject: SubjectResponse
