from uuid import UUID

from sqlalchemy import Uuid
from sqlalchemy.orm import Mapped, mapped_column

from src.projects.projects_db.base import Base


class ParallelConfirmedCandidate(Base):
    """A candidate group the user has marked as reviewed/confirmed.

    Confirmation is tracked at the *candidate* level rather than the subject
    level: each row is a ``candidate_group_id`` (the deterministic id a
    candidate component is emitted under, derived from its subject and member
    blocks). A subject is considered confirmed only when *every* one of its
    current candidate components has a row here.

    Because a candidate's id changes whenever its member blocks change, a stored
    id silently stops matching once the underlying blocks are edited. The
    candidates endpoint reconciles against the freshly-computed components on
    every read: ids that no longer belong to a fully-confirmed subject (stale
    ids, or ids of a subject only partially confirmed) are pruned, so a subject
    never appears confirmed unless all of its live candidates are.
    """

    __tablename__ = "parallel_confirmed_candidates"

    candidate_group_id: Mapped[UUID] = mapped_column(
        Uuid(native_uuid=False),
        primary_key=True,
    )

    def __str__(self) -> str:
        return f"ParallelConfirmedCandidate(candidate_group_id={self.candidate_group_id})"

    __repr__ = __str__
