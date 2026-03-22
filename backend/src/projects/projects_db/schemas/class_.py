from uuid import UUID

from pydantic import BaseModel


class ClassStats(BaseModel):
    id: UUID

    degree_id: UUID
    degree_acronym: str
    degree_name: str

    year_id: UUID
    year_number: int

    code: str
    shift: int

    sessions: int
