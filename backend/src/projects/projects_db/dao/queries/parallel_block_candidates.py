from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Select, and_, func, select
from sqlalchemy.orm import aliased

from src.projects.projects_db.models.class_ import Class
from src.projects.projects_db.models.degree import Degree
from src.projects.projects_db.models.session import Session
from src.projects.projects_db.models.session_class_subject import SessionClassSubject
from src.projects.projects_db.models.subject import Subject
from src.projects.projects_db.models.year import Year


def candidate_edges_stmt() -> Select:
    """Select distinct undirected ``(block_a, block_b)`` parallel-candidate edges.

    Two blocks are adjacent when they share at least one session at the same
    ``(week, weekday, start_time)`` for the same subject, i.e. they collide on
    at least one week. ``block_a < block_b`` keeps each undirected edge once and
    excludes self-pairs.
    """
    left = aliased(Session, name="left_session")
    right = aliased(Session, name="right_session")
    left_scs = aliased(SessionClassSubject, name="left_scs")
    right_scs = aliased(SessionClassSubject, name="right_scs")

    return (
        select(
            left.original_block_id.label("block_a"),
            right.original_block_id.label("block_b"),
        )
        .join(left_scs, left_scs.session_id == left.id)
        .join(
            right,
            and_(
                right.week == left.week,
                right.weekday == left.weekday,
                right.start_time == left.start_time,
            ),
        )
        .join(
            right_scs,
            and_(
                right_scs.session_id == right.id,
                right_scs.subject_id == left_scs.subject_id,
            ),
        )
        .where(left.original_block_id < right.original_block_id)
        .distinct()
    )


def block_details_stmt(block_ids: Sequence[UUID]) -> Select:
    """Select per-``(block, class)`` display details for the given blocks.

    Weeks are intentionally not selected so ``distinct`` collapses a block's
    weekly recurrence into one row per class. A block with classes across
    several years/degrees yields one row per ``(class, year, degree)``; the
    caller picks a representative and aggregates the class codes.
    """
    return (
        select(
            Session.original_block_id.label("original_block_id"),
            Session.weekday.label("weekday"),
            Session.start_time.label("start_time"),
            Session.duration.label("duration"),
            Session.type.label("session_type"),
            Subject.name.label("subject_name"),
            Class.code.label("class_code"),
            Year.number.label("year"),
            Degree.id.label("degree_id"),
            Degree.name.label("degree_name"),
            Degree.acronym.label("degree_acronym"),
        )
        .join(SessionClassSubject, SessionClassSubject.session_id == Session.id)
        .join(Subject, Subject.id == SessionClassSubject.subject_id)
        .join(Class, Class.id == SessionClassSubject.class_id)
        .join(Year, Year.id == Class.year_id)
        .join(Degree, Degree.id == Year.degree_id)
        .where(Session.original_block_id.in_(block_ids))
        .distinct()
    )


def block_weeks_stmt(block_ids: Sequence[UUID]) -> Select:
    """Select ``(first_week, last_week)`` for each of the given blocks."""
    return (
        select(
            Session.original_block_id.label("original_block_id"),
            func.min(Session.week).label("first_week"),
            func.max(Session.week).label("last_week"),
        )
        .where(Session.original_block_id.in_(block_ids))
        .group_by(Session.original_block_id)
    )
