from datetime import date
from uuid import UUID

from pydantic import BaseModel

from src.projects.projects_db.schemas.weekday import WeekDay


class ParallelBlockCandidateNode(BaseModel):
    """A single block within a candidate group, with its display info.

    ``confirmed_group_id`` is the ``parallel_block_group_id`` this block is
    already saved under, or ``None`` if it is not part of a confirmed group.
    """

    original_block_id: UUID
    class_codes: list[str]
    session_type: str
    session_duration: int
    first_week: date
    last_week: date
    year: int
    degree_id: UUID
    degree_name: str
    degree_acronym: str
    confirmed_group_id: UUID | None = None


class ParallelBlockCandidateGroupResponse(BaseModel):
    """A connected component of the parallel-candidate overlap graph.

    ``nodes`` are the blocks; ``edges`` are the undirected adjacency pairs
    (blocks that collide on at least one week). A selection is valid only if
    its blocks form a connected subgraph of these edges. ``subject_name``,
    ``session_weekday`` and ``session_start_time`` are shared by every node.
    """

    candidate_group_id: UUID
    subject_name: str
    session_weekday: WeekDay
    session_start_time: int
    nodes: list[ParallelBlockCandidateNode]
    edges: list[tuple[UUID, UUID]]
