from uuid import UUID

from pydantic import BaseModel


class SubjectStats(BaseModel):
    id: UUID

    degree_id: UUID
    degree_acronym: str
    degree_name: str

    year_id: UUID
    year_number: int

    number: int
    code: str
    acronym: str
    name: str

    sessions: int
