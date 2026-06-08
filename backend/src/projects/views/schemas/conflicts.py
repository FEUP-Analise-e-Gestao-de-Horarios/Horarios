from pydantic import BaseModel

from src.projects.services.schemas.conflicts import ConflictResult


class ConflictsResponse(BaseModel):
    conflicts: list[ConflictResult]
    count: int
