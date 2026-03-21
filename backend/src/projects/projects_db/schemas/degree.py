from uuid import UUID

from pydantic import BaseModel


class DegreeStats(BaseModel):
    id: UUID
    acronym: str
    name: str
    num_years: int
    num_subjects: int
    num_classes: int
    num_sessions: int
