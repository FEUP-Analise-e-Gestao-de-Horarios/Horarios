from pydantic import BaseModel


class ProjectStatsResponse(BaseModel):
    rooms: int
    teachers: int

    degrees: int
    years: int
    subjects: int

    classes: int
    sessions: int
