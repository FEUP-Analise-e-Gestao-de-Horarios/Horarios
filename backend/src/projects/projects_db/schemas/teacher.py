from uuid import UUID

from pydantic import BaseModel


class TeacherStats(BaseModel):
    id: UUID

    number: int
    acronym: str
    name: str

    subjects: int
    classes: int
    sessions: int
