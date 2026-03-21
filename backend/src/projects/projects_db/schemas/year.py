from uuid import UUID

from pydantic import BaseModel


class YearStats(BaseModel):
    id: UUID
    number: int
    degree_id: UUID
    degree_acronym: str
    degree_name: str
    num_subjects: int
    num_classes: int
    num_sessions: int
