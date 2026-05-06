from uuid import UUID

from pydantic import BaseModel


class ClassStats(BaseModel):
    id: UUID
    year_id: UUID

    code: str
    shift: int

    sessions: int
