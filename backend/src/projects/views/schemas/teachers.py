from pydantic import BaseModel


class TeacherStatsResponse(BaseModel):
    id: str
    number: int
    acronym: str
    name: str
    num_sessions: int


class ProjectTeachersResponse(BaseModel):
    teachers: list[TeacherStatsResponse]
    count: int
