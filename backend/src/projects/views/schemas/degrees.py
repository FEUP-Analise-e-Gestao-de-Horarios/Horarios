from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProjectDegreesResponse(BaseModel):
    degrees: list[DegreeStatsResponse]
    count: int


class DegreeStatsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

    acronym: str
    name: str

    years: int
    subjects: int
    classes: int
    sessions: int


class ProjectYearsResponse(BaseModel):
    years: list[YearStatsResponse]
    count: int


class YearStatsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    degree_id: UUID
    degree_acronym: str
    degree_name: str

    number: int

    subjects: int
    classes: int
    sessions: int
