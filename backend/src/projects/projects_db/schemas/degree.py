from uuid import UUID

from pydantic import BaseModel


class DegreeStats(BaseModel):
    id: UUID

    acronym: str
    name: str
    years: int

    subjects: int
    classes: int
    sessions: int
