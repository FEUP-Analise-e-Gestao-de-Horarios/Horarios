from uuid import UUID

from pydantic import BaseModel


class SubjectStats(BaseModel):
    id: UUID

    number: int
    code: str
    acronym: str
    name: str

    sessions: int
