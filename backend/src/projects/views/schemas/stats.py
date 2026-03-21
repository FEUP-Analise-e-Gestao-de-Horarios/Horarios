from pydantic import BaseModel


class ProjectStatsResponse(BaseModel):
    degrees: int
    years: int
    subjects: int
    classes: int
    teachers: int
    rooms: int
    sessions: int
