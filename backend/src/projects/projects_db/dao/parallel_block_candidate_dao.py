from collections import defaultdict
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.projects.projects_db.models.parallel_block_candidate import ParallelBlockCandidate


class ParallelBlockCandidateDAO:
    """Data access object for ParallelBlockCandidate records.

    Not a ``BaseDAO`` subclass: ``ParallelBlockCandidate`` has a composite
    primary key, and ``BaseDAO.get`` / ``delete_by_id`` assume a single-UUID
    PK. None of the inherited helpers fit, so this DAO operates on the
    SQLAlchemy ``Session`` directly.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    # -------------------------------------------------------------------
    # -- Get
    # -------------------------------------------------------------------

    def get_all_groups(self) -> dict[UUID, set[UUID]]:
        """Return all candidate groups, keyed by ``candidate_group_id``."""
        rows = self.session.scalars(
            select(ParallelBlockCandidate).order_by(ParallelBlockCandidate.candidate_group_id),
        ).all()

        groups: defaultdict[UUID, set[UUID]] = defaultdict(set)
        for row in rows:
            groups[row.candidate_group_id].add(row.original_block_id)
        return groups
