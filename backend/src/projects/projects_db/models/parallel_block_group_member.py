from uuid import UUID

from sqlalchemy import UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.projects.projects_db.base import Base


class ParallelBlockGroupMember(Base):
    """A block's membership in a user-confirmed parallel group.

    Each row says "this ``original_block_id`` belongs to this
    ``parallel_block_group_id``". The group itself has no separate row — it
    is just an opaque UUID label that groups membership rows together,
    analogous to how ``sessions.original_block_id`` groups sessions without
    a backing ``blocks`` table. A group "exists" iff it has at least one
    member row.

    The UNIQUE constraint on ``original_block_id`` ensures a block belongs
    to at most one confirmed group, so the move-together semantics are
    unambiguous.
    """

    __tablename__ = "parallel_block_group_members"
    __table_args__ = (
        UniqueConstraint("original_block_id", name="uq_parallel_block_group_members_block"),
    )

    parallel_block_group_id: Mapped[UUID] = mapped_column(
        Uuid(native_uuid=False),
        primary_key=True,
    )
    original_block_id: Mapped[UUID] = mapped_column(
        Uuid(native_uuid=False),
        primary_key=True,
    )

    def __str__(self) -> str:
        return (
            f"ParallelBlockGroupMember(group={self.parallel_block_group_id}, "
            f"block={self.original_block_id})"
        )

    __repr__ = __str__
