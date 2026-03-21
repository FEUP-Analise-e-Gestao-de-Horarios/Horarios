from pydantic import BaseModel


class ProjectOverviewStats(BaseModel):
    num_degrees: int
    num_years: int
    num_subjects: int
    num_classes: int
    num_teachers: int
    num_rooms: int
    num_sessions: int
