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
