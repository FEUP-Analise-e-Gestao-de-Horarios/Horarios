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

    def get_blocks(self, group_id: UUID) -> list[UUID]:
        """Return all block ids in the given confirmed group.

        Returns an empty list if the group has no members (i.e. does not exist).
        """
        return list(
            self.session.scalars(
                select(ParallelBlockGroupMember.original_block_id).where(
                    ParallelBlockGroupMember.parallel_block_group_id == group_id,
                ),
            ).all(),
        )

    def get_all_groups(self) -> dict[UUID, list[UUID]]:
        """Return all confirmed groups, keyed by ``parallel_block_group_id``."""
        rows = self.session.scalars(select(ParallelBlockGroupMember)).all()

        groups: dict[UUID, list[UUID]] = {}
        for row in rows:
            groups.setdefault(row.parallel_block_group_id, []).append(row.original_block_id)
        return groups

    def get_group_id_by_block(self, original_block_id: UUID) -> UUID | None:
        """Return the group id that contains the given block, if any."""
        return self.session.scalars(
            select(ParallelBlockGroupMember.parallel_block_group_id).where(
                ParallelBlockGroupMember.original_block_id == original_block_id,
            ),
        ).one_or_none()

    def get_siblings(self, original_block_id: UUID) -> list[UUID]:
        """Return the other blocks in the same confirmed group as the given block.

        Returns an empty list if the block is not in any confirmed group.
        """
        group_id = self.get_group_id_by_block(original_block_id)
        if group_id is None:
            return []
        return [block_id for block_id in self.get_blocks(group_id) if block_id != original_block_id]

    # -------------------------------------------------------------------
    # -- Update
    # -------------------------------------------------------------------

    def add_member(self, group_id: UUID, block_id: UUID) -> None:
        """Add a block to an existing confirmed group.

        Raises:
            ValueError: If the group does not exist (no members), or the
                block already belongs to a confirmed group.
        """
        group_exists = self.session.scalars(
            select(ParallelBlockGroupMember.original_block_id)
            .where(ParallelBlockGroupMember.parallel_block_group_id == group_id)
            .limit(1),
        ).first()
        if group_exists is None:
            raise ValueError(f"ParallelBlockGroup {group_id} not found")

        existing_group = self.get_group_id_by_block(block_id)
        if existing_group is not None:
            raise ValueError(f"Block {block_id} already belongs to a confirmed group")

        self.session.execute(
            insert(ParallelBlockGroupMember),
            [{"parallel_block_group_id": group_id, "original_block_id": block_id}],
        )

    def remove_member(self, group_id: UUID, block_id: UUID) -> bool:
        """Remove a block from a confirmed group.

        Returns:
            True if a member was removed, False if no matching member existed.
        """
        result = self.session.execute(
            delete(ParallelBlockGroupMember).where(
                ParallelBlockGroupMember.parallel_block_group_id == group_id,
                ParallelBlockGroupMember.original_block_id == block_id,
            ),
        )
        return result.rowcount > 0

    # -------------------------------------------------------------------
    # -- Delete
    # -------------------------------------------------------------------

    def delete_group(self, group_id: UUID) -> bool:
        """Delete all members of a confirmed group.

        Returns:
            True if any rows were removed, False if the group did not exist.
        """
        result = self.session.execute(
            delete(ParallelBlockGroupMember).where(
                ParallelBlockGroupMember.parallel_block_group_id == group_id,
            ),
        )
        return result.rowcount > 0
