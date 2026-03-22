from uuid import UUID

from pydantic import BaseModel


class YearStats(BaseModel):
    id: UUID
    degree_id: UUID

    number: int

    degree_acronym: str
    degree_name: str

    subjects: int
    classes: int
    sessions: int
