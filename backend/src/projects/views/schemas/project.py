import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator


# -- Projects list -----------------------------------------------------
class ProjectsResponse(BaseModel):
    projects: list[ProjectResponse]
    count: int


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    url: str

    has_selected_aulas_em_paralelo: bool

    ingestion_started_at: datetime | None
    ingestion_finished_at: datetime | None
    ingestion_failed_at: datetime | None

    created_at: datetime
    updated_at: datetime


# -- Create project ----------------------------------------------------
class CreateProjectRequest(BaseModel):
    name: str = Field(max_length=30)
    url: HttpUrl

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.fullmatch(r"[a-zA-Z0-9_\-: ]+", v):
            raise ValueError("name can only contain letters, numbers, spaces, '_', '-' and ':'")
        return v


class CreateProjectResponse(BaseModel):
    id: int
    name: str


# -- Rename project ----------------------------------------------------
class RenameProjectRequest(BaseModel):
    name: str = Field(max_length=30)

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not re.fullmatch(r"[a-zA-Z0-9_\-: ]+", v):
            raise ValueError("name can only contain letters, numbers, spaces, '_', '-' and ':'")
        return v
