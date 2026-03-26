from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ClassInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    code: str
    shift: int


class SessionParallelClasses(BaseModel):
    session: UUID
    classes: list[ClassInfo]
