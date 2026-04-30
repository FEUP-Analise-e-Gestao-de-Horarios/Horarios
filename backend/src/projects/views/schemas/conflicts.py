from pydantic import BaseModel


class ConflictResponse(BaseModel):
    id: str
    event_ids: list[str]
    event_names: list[str]
    day: str
    time: str
    turma: str
    conflict_reasons: list[str]


class ConflictsResponse(BaseModel):
    conflicts: list[ConflictResponse]
    count: int
