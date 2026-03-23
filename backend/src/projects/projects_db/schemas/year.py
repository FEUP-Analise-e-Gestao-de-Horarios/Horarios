from uuid import UUID

from pydantic import BaseModel


class YearStats(BaseModel):
    id: UUID
    degree_id: UUID
    degree_acronym: str
    degree_name: str

    number: int

    subjects: int
    classes: int
    sessions: int
