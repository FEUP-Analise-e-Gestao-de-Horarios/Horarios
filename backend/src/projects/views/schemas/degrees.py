from pydantic import BaseModel


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
