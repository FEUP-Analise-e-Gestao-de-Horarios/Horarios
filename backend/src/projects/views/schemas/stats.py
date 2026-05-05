from pydantic import BaseModel


# -- Project stats -----------------------------------------------------
class StatsResponse(BaseModel):
    rooms: int
    teachers: int

    degrees: int
    years: int
    subjects: int

    classes: int
    sessions: int
