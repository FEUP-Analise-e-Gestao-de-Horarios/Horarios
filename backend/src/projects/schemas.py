import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

# -------------------------------------------------------------------
# -- Get
# -------------------------------------------------------------------


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: str

    has_selected_aulas_em_paralelo: bool
    started_ingestion_at: datetime | None
    finished_ingestion_at: datetime | None
    failed_ingestion_at: datetime | None


class ProjectsResponse(BaseModel):
    projects: list[ProjectResponse]
    count: int


# -------------------------------------------------------------------
# -- Create
# -------------------------------------------------------------------


class CreateProjectRequest(BaseModel):
    name: str = Field(max_length=30)
    url: HttpUrl

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.fullmatch(r"[a-zA-Z0-9_\- ]+", v):
            raise ValueError("name can only contain letters, numbers, spaces, '_' and '-'")
        return v


class CreateProjectResponse(BaseModel):
    id: int
    name: str


# -------------------------------------------------------------------
# -- Degrees
# -------------------------------------------------------------------


class DegreeStatsResponse(BaseModel):
    id: str
    acronym: str
    name: str
    num_years: int
    num_subjects: int
    num_classes: int
    num_sessions: int


class ProjectDegreesResponse(BaseModel):
    degrees: list[DegreeStatsResponse]
    count: int


# -------------------------------------------------------------------
# -- Years
# -------------------------------------------------------------------


class YearStatsResponse(BaseModel):
    id: str
    number: int
    degree_id: str
    degree_acronym: str
    degree_name: str
    num_subjects: int
    num_classes: int
    num_sessions: int


class ProjectYearsResponse(BaseModel):
    years: list[YearStatsResponse]
    count: int


# -------------------------------------------------------------------
# -- Rooms
# -------------------------------------------------------------------


class RoomStatsResponse(BaseModel):
    id: str
    name: str
    type: str | None
    size: str | None
    seats: str | None
    num_sessions: int


class ProjectRoomsResponse(BaseModel):
    rooms: list[RoomStatsResponse]
    count: int


# -------------------------------------------------------------------
# -- Edit
# -------------------------------------------------------------------


class RenameProjectRequest(BaseModel):
    name: str = Field(max_length=30)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.fullmatch(r"[a-zA-Z0-9_\- ]+", v):
            raise ValueError("name can only contain letters, numbers, spaces, '_' and '-'")
        return v
