from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from src.projects.projects_db.models.parallel_confirmed_candidate import ParallelConfirmedCandidate


class ParallelConfirmedCandidateDAO:
    """Data access object for user-confirmed parallel candidate groups.

    Each row is a single ``candidate_group_id`` the user has reviewed. There is
    no subject column: subject-level confirmation is derived by the candidate
    DAO, which owns the mapping from candidates to subjects.

    Not a ``BaseDAO`` subclass: the table is a single-column set of ids, so none
    of the inherited single-UUID-PK helpers fit.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_all(self) -> set[UUID]:
        """Return every confirmed ``candidate_group_id``."""
        return set(
            self.session.scalars(select(ParallelConfirmedCandidate.candidate_group_id)).all(),
        )

    def add(self, candidate_group_ids: Iterable[UUID]) -> list[UUID]:
        """Mark the given candidate groups confirmed, ignoring any already stored.

        Returns the full (deduplicated) list of ids requested.
        """
        ids = list(dict.fromkeys(candidate_group_ids))
        if not ids:
            return []
        existing = set(
            self.session.scalars(
                select(ParallelConfirmedCandidate.candidate_group_id).where(
                    ParallelConfirmedCandidate.candidate_group_id.in_(ids),
                ),
            ).all(),
        )
        new_ids = [cid for cid in ids if cid not in existing]
        if new_ids:
            self.session.execute(
                insert(ParallelConfirmedCandidate),
                [{"candidate_group_id": cid} for cid in new_ids],
            )
        return ids

    def remove(self, candidate_group_ids: Iterable[UUID]) -> int:
        """Delete the given candidate groups from the confirmed set.

        Returns the number of rows removed.
        """
        ids = list(dict.fromkeys(candidate_group_ids))
        if not ids:
            return 0

        result = self.session.execute(
            delete(ParallelConfirmedCandidate).where(
                ParallelConfirmedCandidate.candidate_group_id.in_(ids),
            ),
        )
        return result.rowcount

    def retain_only(self, keep: set[UUID]) -> int:
        """Delete every stored id not in ``keep``.

        Returns the number of rows removed.
        """
        if not keep:
            return self.clear_all()

        result = self.session.execute(
            delete(ParallelConfirmedCandidate).where(
                ParallelConfirmedCandidate.candidate_group_id.notin_(keep),
            ),
        )
        return result.rowcount

    def clear_all(self) -> int:
        """Delete every confirmed candidate. Returns the number of rows removed."""
        result = self.session.execute(delete(ParallelConfirmedCandidate))
        return result.rowcount
