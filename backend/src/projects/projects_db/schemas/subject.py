from uuid import UUID

from pydantic import BaseModel


class SubjectStats(BaseModel):
    id: UUID
    number: int
    code: str
    acronym: str
    name: str
    year_id: UUID
    year_number: int
    degree_id: UUID
    degree_acronym: str
    degree_name: str
    num_sessions: int
