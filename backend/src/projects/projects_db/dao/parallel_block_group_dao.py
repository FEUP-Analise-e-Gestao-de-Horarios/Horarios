import uuid
from collections.abc import Iterable
from uuid import UUID

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from src.projects.projects_db.models.parallel_block_group_member import ParallelBlockGroupMember


class ParallelBlockGroupDAO:
    """Data access object for user-confirmed parallel block groups.

    A "group" is an opaque ``parallel_block_group_id`` UUID shared by a set
    of membership rows in ``parallel_block_group_members``. There is no
    separate header table — a group exists iff it has at least one member.
    A block belongs to at most one confirmed group (enforced by the UNIQUE
    constraint on ``original_block_id``).

    Not a ``BaseDAO`` subclass: ``ParallelBlockGroupMember`` has a composite
    primary key, and ``BaseDAO.get`` / ``delete_by_id`` assume a single-UUID
    PK. None of the inherited helpers fit, so this DAO operates on the
    SQLAlchemy ``Session`` directly.
    """

    def __init__(self, session: Session) -> None:
        self.session = session

    # -------------------------------------------------------------------
    # -- Create
    # -------------------------------------------------------------------

    def create(self, member_block_ids: Iterable[UUID]) -> UUID:
        """Create a new confirmed parallel group with the given members.

        Args:
            member_block_ids: ``original_block_id`` values to include in the
                new group. Must contain at least two distinct blocks, and
                none may already belong to another confirmed group.

        Returns:
            The freshly generated ``parallel_block_group_id``.

        Raises:
            ValueError: If fewer than two distinct blocks are provided, or
                if any of the blocks already belongs to a confirmed group.
        """
        unique_block_ids = list(dict.fromkeys(member_block_ids))
        if len(unique_block_ids) < 2:
            raise ValueError("A parallel block group must contain at least two blocks")

        already_grouped = self.session.scalars(
            select(ParallelBlockGroupMember.original_block_id).where(
                ParallelBlockGroupMember.original_block_id.in_(unique_block_ids),
            ),
        ).all()
        if already_grouped:
            raise ValueError(
                f"Blocks already belong to a confirmed group: {sorted(map(str, already_grouped))}",
            )

        group_id = uuid.uuid7()
        self.session.execute(
            insert(ParallelBlockGroupMember),
            [
                {"parallel_block_group_id": group_id, "original_block_id": block_id}
                for block_id in unique_block_ids
            ],
        )
        return group_id

    # -------------------------------------------------------------------
    # -- Get
    # -------------------------------------------------------------------

    def get_all_groups(self) -> dict[UUID, list[UUID]]:
        """Return all confirmed groups, keyed by ``parallel_block_group_id``."""
        rows = self.session.scalars(select(ParallelBlockGroupMember)).all()

        groups: dict[UUID, list[UUID]] = {}
        for row in rows:
            groups.setdefault(row.parallel_block_group_id, []).append(row.original_block_id)
        return groups

    # -------------------------------------------------------------------
    # -- Delete
    # -------------------------------------------------------------------

    def clear_all(self) -> int:
        """Delete all confirmed parallel group members across every group.

        Returns:
            The number of rows deleted.
        """
        result = self.session.execute(delete(ParallelBlockGroupMember))
        return result.rowcount
