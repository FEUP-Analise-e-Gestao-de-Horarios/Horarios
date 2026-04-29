from uuid import UUID

from pydantic import BaseModel


class ParallelGroupEntry(BaseModel):
    classes: list[UUID]


class SaveParallelGroupMembersRequest(BaseModel):
    groups: list[ParallelGroupEntry]
