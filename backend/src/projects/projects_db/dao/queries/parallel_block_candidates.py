from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import Select, func, select

from src.projects.projects_db.models.class_ import Class
from src.projects.projects_db.models.degree import Degree
from src.projects.projects_db.models.session import Session
from src.projects.projects_db.models.session_class_subject import SessionClassSubject
from src.projects.projects_db.models.subject import Subject
from src.projects.projects_db.models.year import Year


def candidate_slot_members_stmt(subject_id: UUID | None = None) -> Select:
    """Select ``(slot, subject, block)`` rows for candidate detection.

    A "slot" is ``(week, weekday, start_time)``. Two blocks are parallel
    candidates when they appear in the same slot for the same subject; grouping
    these rows by ``(week, weekday, start_time, subject_id)`` yields the overlap
    graph's edges (blocks sharing a slot are mutually adjacent) without the
    quadratic ``sessions``-self-join SQLite cannot index efficiently.

    When ``subject_id`` is given, only that subject's rows are scanned. A
    subject's components depend solely on its own rows (the grouping key
    includes ``subject_id``, and every session of a block carries the block's
    full, fixed set of subjects -- see ``_assign_block_ids``), so the filtered
    scan yields that subject's components identically to the full scan while
    reading far fewer rows. When ``None`` the full graph is scanned.

    Not de-duplicated in SQL on purpose: the caller groups blocks into a ``set``
    per slot, which already collapses duplicates, so a SQL ``DISTINCT`` would
    only add a needless sort over every session row.
    """
    stmt = select(
        Session.week.label("week"),
        Session.weekday.label("weekday"),
        Session.start_time.label("start_time"),
        SessionClassSubject.subject_id.label("subject_id"),
        Session.original_block_id.label("original_block_id"),
    ).join(SessionClassSubject, SessionClassSubject.session_id == Session.id)
    if subject_id is not None:
        stmt = stmt.where(SessionClassSubject.subject_id == subject_id)
    return stmt


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
            Subject.id.label("subject_id"),
            Subject.acronym.label("subject_acronym"),
            Subject.name.label("subject_name"),
            Class.id.label("class_id"),
            Class.code.label("class_code"),
            Year.id.label("year_id"),
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
