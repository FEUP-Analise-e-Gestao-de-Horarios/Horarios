from pydantic import BaseModel


class SubjectStatsResponse(BaseModel):
    id: str
    number: int
    code: str
    acronym: str
    name: str
    year_id: str
    year_number: int
    degree_id: str
    degree_acronym: str
    degree_name: str
    num_sessions: int


class ProjectSubjectsResponse(BaseModel):
    subjects: list[SubjectStatsResponse]
    count: int


class ClassStatsResponse(BaseModel):
    id: str
    code: str
    shift: int
    year_id: str
    year_number: int
    degree_id: str
    degree_acronym: str
    degree_name: str
    num_sessions: int


class ProjectClassesResponse(BaseModel):
    classes: list[ClassStatsResponse]
    count: int
