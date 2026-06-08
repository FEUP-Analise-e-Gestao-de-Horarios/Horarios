from pydantic import BaseModel


class ConflictResult(BaseModel):
    id: str
    event_ids: list[str]
    event_names: list[str]
    day: str
    time: int
    turma: list[str]
    conflict_reasons: list[str]
