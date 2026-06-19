from uuid import UUID

from pydantic import BaseModel


class ParallelGroupEntry(BaseModel):
    candidate_group_id: UUID
    classes: list[UUID]


class SaveParallelGroupMembersRequest(BaseModel):
    groups: list[ParallelGroupEntry]
