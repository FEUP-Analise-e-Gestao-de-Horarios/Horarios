from datetime import date
from uuid import UUID

from pydantic import BaseModel

from src.projects.projects_db.schemas.weekday import WeekDay


class ParallelBlockCandidateClass(BaseModel):
    """A class taught by the block, with the year it belongs to."""

    id: UUID
    code: str
    year_id: UUID


class ParallelBlockCandidateSession(BaseModel):
    """The session template shared by a block's weekly occurrences."""

    type: str
    start_time: int
    duration: int


class ParallelBlockCandidateNode(BaseModel):
    """A single block within a candidate group, with its display info.

    Each class carries the group's ``subject.years`` row it belongs to via its
    ``year_id`` (a block may span several year/degree rows); resolve degree info
    there.

    ``confirmed_group_id`` is the ``parallel_block_group_id`` this block is
    already saved under, or ``None`` if it is not part of a confirmed group.
    """

    original_block_id: UUID
    confirmed_group_id: UUID | None = None
    first_week: date
    last_week: date
    session: ParallelBlockCandidateSession
    classes: list[ParallelBlockCandidateClass]


class ParallelBlockCandidateDegree(BaseModel):
    """A degree that teaches the candidate group's subject."""

    id: UUID
    acronym: str
    name: str


class ParallelBlockCandidateYear(BaseModel):
    """An academic year row the candidate group's subject is taught in.

    Each ``years`` row belongs to a single degree.
    """

    id: UUID
    degree: ParallelBlockCandidateDegree


class ParallelBlockCandidateSubject(BaseModel):
    """The subject shared by every block in a candidate group.

    ``years`` lists only the year/degree combinations present in this group.
    """

    id: UUID
    acronym: str
    name: str
    years: list[ParallelBlockCandidateYear]


class ParallelBlockCandidateEdge(BaseModel):
    """An undirected adjacency between two blocks of a candidate group.

    ``source`` and ``target`` are the two blocks' ``original_block_id``s; the
    edge is undirected, so their order carries no meaning. ``weeks`` lists every
    week on which the two blocks collide (same weekday and start time).
    """

    source: UUID
    target: UUID
    weeks: list[date]


class ParallelBlockCandidateGroupResponse(BaseModel):
    """A connected component of the parallel-candidate overlap graph.

    ``nodes`` are the blocks; ``edges`` are the undirected adjacencies (blocks
    that collide on at least one week, each carrying those overlapping weeks). A
    selection is valid only if its blocks form a connected subgraph of these
    edges. ``subject`` and ``weekday`` are shared by every node.
    """

    candidate_group_id: UUID
    weekday: WeekDay
    subject: ParallelBlockCandidateSubject
    nodes: list[ParallelBlockCandidateNode]
    edges: list[ParallelBlockCandidateEdge]
