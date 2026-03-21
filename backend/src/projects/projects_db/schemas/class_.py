from uuid import UUID

from pydantic import BaseModel


class ClassStats(BaseModel):
    id: UUID
    code: str
    shift: int
    year_id: UUID
    year_number: int
    degree_id: UUID
    degree_acronym: str
    degree_name: str
    num_sessions: int
