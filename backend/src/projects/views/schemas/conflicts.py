"""Response schemas for conflict detection."""

from pydantic import BaseModel


class ConflictRecordSchema(BaseModel):
    id: str
    event_ids: list[str]
    event_names: list[str]
    day: str
    time: str
    turma: str
    conflict_reasons: list[str]


class ConflictsResponse(BaseModel):
    conflicts: list[ConflictRecordSchema]
    count: int
