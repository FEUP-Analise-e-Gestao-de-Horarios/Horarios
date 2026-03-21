from pydantic import BaseModel


class ProjectOverviewStats(BaseModel):
    degrees: int
    years: int
    subjects: int
    classes: int
    teachers: int
    rooms: int
    sessions: int
