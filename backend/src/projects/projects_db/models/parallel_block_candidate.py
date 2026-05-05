from uuid import UUID

from sqlalchemy import Index, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.projects.projects_db.base import Base


class ParallelBlockCandidate(Base):
    """A block detected as a candidate for running in parallel with other blocks.

    Populated once at the end of ingestion from the parallel-block detection
    query. Each ``candidate_group_id`` collects the original block ids that
    coincide on ``(week, weekday, start_time, subject_id)`` in their first
    week of occurrence. Treated as immutable post-ingestion.
    """

    __tablename__ = "parallel_block_candidates"
    __table_args__ = (Index("ix_parallel_block_candidates_original_block_id", "original_block_id"),)

    candidate_group_id: Mapped[UUID] = mapped_column(
        Uuid(native_uuid=False),
        primary_key=True,
    )
    original_block_id: Mapped[UUID] = mapped_column(
        Uuid(native_uuid=False),
        primary_key=True,
    )

    def __str__(self) -> str:
        return (
            f"ParallelBlockCandidate(group={self.candidate_group_id}, "
            f"block={self.original_block_id})"
        )

    __repr__ = __str__
