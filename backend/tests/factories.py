"""Row builders for the per-project SQLAlchemy database.

Plain functions, not a factory framework: each ``make_*`` helper inserts one
row (or the minimal set of linked rows) with sensible defaults, lets the caller
override any field, and commits by default so the endpoint under test — which
opens its own session — sees the data. Pass ``commit=False`` to batch several
inserts and commit once at the end.

Ids default to ``uuid.uuid7`` where a model has no server default (all of them
do default it, but passing an explicit id keeps tests deterministic and lets a
caller wire up relationships by id without a flush).
"""

import datetime
import uuid
from uuid import UUID

from sqlalchemy import insert
from sqlalchemy.orm import Session

from src.projects.projects_db.models import (
    Class,
    Degree,
    ParallelBlockGroupMember,
    SessionClassSubject,
    Subject,
    Year,
)
from src.projects.projects_db.models import (
    Session as SessionModel,
)
from src.projects.projects_db.models._secondary_tables import subject_years
from src.projects.projects_db.schemas.weekday import WeekDay


def _finish[T](session: Session, obj: T, *, commit: bool) -> T:
    session.add(obj)
    if commit:
        session.commit()
    else:
        session.flush()
    return obj


def make_degree(
    session: Session,
    *,
    id: UUID | None = None,
    acronym: str = "LEI",
    name: str = "Licenciatura em Engenharia Informática",
    commit: bool = True,
) -> Degree:
    """Insert a ``Degree`` row."""
    degree = Degree(id=id or uuid.uuid7(), acronym=acronym, name=name)
    return _finish(session, degree, commit=commit)


def make_year(
    session: Session,
    *,
    degree: Degree | None = None,
    id: UUID | None = None,
    number: int = 1,
    commit: bool = True,
) -> Year:
    """Insert a ``Year`` row, creating a parent ``Degree`` if none is given."""
    if degree is None:
        degree = make_degree(session, commit=False)
    year = Year(id=id or uuid.uuid7(), degree_id=degree.id, number=number)
    return _finish(session, year, commit=commit)


def make_subject(
    session: Session,
    *,
    year: Year | None = None,
    id: UUID | None = None,
    number: int | None = None,
    code: str | None = None,
    acronym: str = "PROG",
    name: str = "Programação",
    commit: bool = True,
) -> Subject:
    """Insert a ``Subject`` and link it to ``year`` via the ``subject_years`` m2m.

    ``number`` and ``code`` are globally unique; when omitted they are derived
    from a fresh uuid so repeated calls never collide.
    """
    subject_id = id or uuid.uuid7()
    unique = subject_id.int % 1_000_000
    subject = Subject(
        id=subject_id,
        number=number if number is not None else unique,
        code=code if code is not None else f"UC{unique}",
        acronym=acronym,
        name=name,
    )
    session.add(subject)
    session.flush()

    if year is None:
        year = make_year(session, commit=False)
    session.execute(
        insert(subject_years).values(subject_id=subject.id, year_id=year.id),
    )

    if commit:
        session.commit()
    return subject


def make_class(
    session: Session,
    *,
    year: Year | None = None,
    id: UUID | None = None,
    code: str | None = None,
    shift: int = 1,
    commit: bool = True,
) -> Class:
    """Insert a ``Class`` row, creating a parent ``Year`` if none is given."""
    if year is None:
        year = make_year(session, commit=False)
    class_id = id or uuid.uuid7()
    klass = Class(
        id=class_id,
        year_id=year.id,
        code=code if code is not None else f"C{class_id.int % 1_000_000}",
        shift=shift,
    )
    return _finish(session, klass, commit=commit)


def make_session(
    session: Session,
    *,
    id: UUID | None = None,
    week: datetime.date | None = None,
    weekday: WeekDay = WeekDay.MONDAY,
    start_time: int = 9,
    duration: int = 2,
    type: str = "T",
    original_block_id: UUID | None = None,
    commit: bool = True,
) -> SessionModel:
    """Insert a ``Session`` (a single scheduled event) row."""
    session_row = SessionModel(
        id=id or uuid.uuid7(),
        week=week or datetime.date(2025, 9, 15),
        weekday=weekday,
        start_time=start_time,
        duration=duration,
        type=type,
        original_block_id=original_block_id or uuid.uuid7(),
    )
    return _finish(session, session_row, commit=commit)


def make_session_class_subject(
    session: Session,
    *,
    session_row: SessionModel,
    class_row: Class,
    subject: Subject,
    commit: bool = True,
) -> SessionClassSubject:
    """Link a session to a class and the subject taught in it."""
    scs = SessionClassSubject(
        session_id=session_row.id,
        class_id=class_row.id,
        subject_id=subject.id,
    )
    return _finish(session, scs, commit=commit)


def make_group_member(
    session: Session,
    *,
    group_id: UUID,
    original_block_id: UUID,
    commit: bool = True,
) -> ParallelBlockGroupMember:
    """Insert one confirmed-group membership row."""
    member = ParallelBlockGroupMember(
        parallel_block_group_id=group_id,
        original_block_id=original_block_id,
    )
    return _finish(session, member, commit=commit)


def make_parallel_candidate_pair(
    session: Session,
    *,
    subject: Subject | None = None,
    week: datetime.date | None = None,
    weekday: WeekDay = WeekDay.MONDAY,
    start_time: int = 9,
    commit: bool = True,
) -> tuple[UUID, UUID]:
    """Seed the minimum rows so two blocks are detected as parallel candidates.

    Both blocks share the same ``(week, weekday, start_time, subject)`` slot,
    each attached to its own class, which is what
    ``build_candidate_components`` treats as an overlap edge. Returns the two
    ``original_block_id`` values, sorted, so callers can assert on membership.
    """
    week = week or datetime.date(2025, 9, 15)
    if subject is None:
        subject = make_subject(session, commit=False)
        year = subject.years[0]
    else:
        year = subject.years[0] if subject.years else make_year(session, commit=False)

    block_ids: list[UUID] = []
    for _ in range(2):
        class_row = make_class(session, year=year, commit=False)
        block_id = uuid.uuid7()
        session_row = make_session(
            session,
            week=week,
            weekday=weekday,
            start_time=start_time,
            original_block_id=block_id,
            commit=False,
        )
        make_session_class_subject(
            session,
            session_row=session_row,
            class_row=class_row,
            subject=subject,
            commit=False,
        )
        block_ids.append(block_id)

    if commit:
        session.commit()
    return tuple(sorted(block_ids))  # type: ignore[return-value]
