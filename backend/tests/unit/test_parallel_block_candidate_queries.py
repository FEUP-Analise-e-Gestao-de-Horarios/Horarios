"""Statement-level tests for ``dao/queries/parallel_block_candidates.py``.

Placed under ``tests/unit/`` per the harness convention, but these are really
integration-flavoured DAO/query tests: they seed a real per-project SQLite file
(via the ``project_db`` fixture) and execute the ``select`` statements the DAO
builds directly on that session. Reads happen on the same seeding session, which
autoflushes pending writes, so joins resolve without a manual commit.

Coverage targets ``candidate_slot_members_stmt``, ``block_details_stmt`` and
``block_weeks_stmt``, plus the ``WeekDay`` enum round-tripping through the
``Enum(..., native_enum=False)`` column. None of the statements imposes an
``ORDER BY``, so every assertion is against sets/dicts keyed by
``original_block_id`` rather than positional ordering.
"""

import datetime
import uuid

import pytest
from sqlalchemy import insert
from sqlalchemy.orm import Session

from src.projects.projects_db.dao.queries.parallel_block_candidates import (
    block_details_stmt,
    block_weeks_stmt,
    candidate_slot_members_stmt,
)
from src.projects.projects_db.models._secondary_tables import subject_years
from src.projects.projects_db.schemas.weekday import WeekDay
from tests.factories import (
    make_class,
    make_degree,
    make_parallel_candidate_pair,
    make_session,
    make_session_class_subject,
    make_subject,
    make_year,
)

MONDAY_WEEK = datetime.date(2025, 9, 15)


def _attach_block_across_weeks(
    session: Session,
    *,
    block_id: uuid.UUID,
    weeks: list[datetime.date],
    class_row,
    subject,
    weekday: WeekDay = WeekDay.MONDAY,
    start_time: int = 9,
    duration: int = 2,
    type: str = "T",
) -> None:
    """Attach one linked ``Session`` per week to a single ``original_block_id``.

    ``sessions`` is ``UNIQUE(week, original_block_id)`` so recurrence needs
    distinct weeks; every session shares the passed ``block_id`` and gets its
    own ``SessionClassSubject`` link so the inner-join statements keep it.
    """
    for week in weeks:
        session_row = make_session(
            session,
            week=week,
            weekday=weekday,
            start_time=start_time,
            duration=duration,
            type=type,
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


def _link_subject_to_year(session: Session, subject, year) -> None:
    """Add a ``subject_years`` m2m row (a subject may span several years)."""
    session.execute(
        insert(subject_years).values(subject_id=subject.id, year_id=year.id),
    )
    session.flush()


# --------------------------------------------------------------------------- #
# candidate_slot_members_stmt
# --------------------------------------------------------------------------- #


def test_slot_members_labeled_columns_match(project_db: Session) -> None:
    """One fully linked session yields exactly the labeled slot/subject/block."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    klass = make_class(project_db, year=year, commit=False)
    block_id = uuid.uuid7()
    session_row = make_session(
        project_db,
        week=MONDAY_WEEK,
        weekday=WeekDay.MONDAY,
        start_time=9,
        original_block_id=block_id,
        commit=False,
    )
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=klass,
        subject=subject,
        commit=False,
    )

    rows = project_db.execute(candidate_slot_members_stmt()).all()

    assert len(rows) == 1
    (row,) = rows
    assert row.week == MONDAY_WEEK
    assert isinstance(row.week, datetime.date)
    assert row.weekday == WeekDay.MONDAY
    assert isinstance(row.weekday, WeekDay)
    assert row.start_time == 9
    assert row.subject_id == subject.id
    assert row.original_block_id == block_id


def test_slot_members_recurrence_no_distinct(project_db: Session) -> None:
    """A block with three weekly sessions yields three rows differing only by week."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    klass = make_class(project_db, year=year, commit=False)
    block_id = uuid.uuid7()
    weeks = [
        datetime.date(2025, 9, 15),
        datetime.date(2025, 9, 22),
        datetime.date(2025, 9, 29),
    ]
    _attach_block_across_weeks(
        project_db,
        block_id=block_id,
        weeks=weeks,
        class_row=klass,
        subject=subject,
    )

    rows = project_db.execute(candidate_slot_members_stmt()).all()

    assert len(rows) == 3
    assert {r.week for r in rows} == set(weeks)
    # Everything but the week is identical across the recurrence.
    assert {r.weekday for r in rows} == {WeekDay.MONDAY}
    assert {r.start_time for r in rows} == {9}
    assert {r.subject_id for r in rows} == {subject.id}
    assert {r.original_block_id for r in rows} == {block_id}


def test_slot_members_one_session_two_classes(project_db: Session) -> None:
    """One session linked to two classes (same subject) fans out to two rows."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    c1 = make_class(project_db, year=year, commit=False)
    c2 = make_class(project_db, year=year, commit=False)
    block_id = uuid.uuid7()
    session_row = make_session(
        project_db,
        week=MONDAY_WEEK,
        original_block_id=block_id,
        commit=False,
    )
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=c1,
        subject=subject,
        commit=False,
    )
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=c2,
        subject=subject,
        commit=False,
    )

    rows = project_db.execute(candidate_slot_members_stmt()).all()

    assert len(rows) == 2
    assert {r.week for r in rows} == {MONDAY_WEEK}
    assert {r.weekday for r in rows} == {WeekDay.MONDAY}
    assert {r.start_time for r in rows} == {9}
    assert {r.subject_id for r in rows} == {subject.id}
    assert {r.original_block_id for r in rows} == {block_id}


def test_slot_members_two_subjects_distinct_subject_ids(project_db: Session) -> None:
    """One session under two subjects (two classes) emits a row per subject."""
    year = make_year(project_db, commit=False)
    s1 = make_subject(project_db, year=year, acronym="AAA", commit=False)
    s2 = make_subject(project_db, year=year, acronym="BBB", commit=False)
    c1 = make_class(project_db, year=year, commit=False)
    c2 = make_class(project_db, year=year, commit=False)
    block_id = uuid.uuid7()
    session_row = make_session(
        project_db,
        week=MONDAY_WEEK,
        original_block_id=block_id,
        commit=False,
    )
    # uq_session_class(session_id, class_id) forces distinct classes.
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=c1,
        subject=s1,
        commit=False,
    )
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=c2,
        subject=s2,
        commit=False,
    )

    rows = project_db.execute(candidate_slot_members_stmt()).all()

    assert len(rows) == 2
    assert {r.original_block_id for r in rows} == {block_id}
    assert {r.subject_id for r in rows} == {s1.id, s2.id}


def test_slot_members_inner_join_drops_scs_less_session(project_db: Session) -> None:
    """A session with no SessionClassSubject is dropped by the inner join."""
    make_session(project_db, original_block_id=uuid.uuid7(), commit=False)

    rows = project_db.execute(candidate_slot_members_stmt()).all()

    assert rows == []


def test_slot_members_empty_database(project_db: Session) -> None:
    """Schema-only database returns no rows."""
    rows = project_db.execute(candidate_slot_members_stmt()).all()

    assert rows == []


def test_slot_members_two_blocks_share_slot(project_db: Session) -> None:
    """Two candidate blocks sharing one slot both appear."""
    block_a, block_b = make_parallel_candidate_pair(project_db)

    rows = project_db.execute(candidate_slot_members_stmt()).all()

    assert len(rows) == 2
    assert {r.original_block_id for r in rows} == {block_a, block_b}
    assert {r.week for r in rows} == {MONDAY_WEEK}
    assert {r.weekday for r in rows} == {WeekDay.MONDAY}
    assert {r.start_time for r in rows} == {9}
    # Both attached to the single shared subject.
    assert len({r.subject_id for r in rows}) == 1


# --------------------------------------------------------------------------- #
# block_details_stmt
# --------------------------------------------------------------------------- #


def test_block_details_distinct_collapses_recurrence(project_db: Session) -> None:
    """Three identical recurring sessions collapse to one detail row per class."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    klass = make_class(project_db, year=year, commit=False)
    block_id = uuid.uuid7()
    _attach_block_across_weeks(
        project_db,
        block_id=block_id,
        weeks=[
            datetime.date(2025, 9, 15),
            datetime.date(2025, 9, 22),
            datetime.date(2025, 9, 29),
        ],
        class_row=klass,
        subject=subject,
        weekday=WeekDay.MONDAY,
        start_time=9,
        duration=2,
        type="T",
    )

    rows = project_db.execute(block_details_stmt([block_id])).all()

    assert len(rows) == 1
    (row,) = rows
    assert row.original_block_id == block_id
    assert row.class_id == klass.id
    assert row.subject_id == subject.id
    assert row.year_id == year.id
    assert row.degree_id == year.degree_id
    assert row.session_type == "T"
    assert row.duration == 2
    assert row.start_time == 9
    assert row.weekday == WeekDay.MONDAY


def test_block_details_one_row_per_class_year_degree(project_db: Session) -> None:
    """A block whose classes span two year/degree pairs yields one row per pair."""
    subject = make_subject(project_db, commit=False)
    y1 = subject.years[0]
    d2 = make_degree(project_db, acronym="MEI", commit=False)
    y2 = make_year(project_db, degree=d2, number=2, commit=False)
    _link_subject_to_year(project_db, subject, y2)
    c1 = make_class(project_db, year=y1, commit=False)
    c2 = make_class(project_db, year=y2, commit=False)
    block_id = uuid.uuid7()
    session_row = make_session(
        project_db,
        week=MONDAY_WEEK,
        original_block_id=block_id,
        commit=False,
    )
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=c1,
        subject=subject,
        commit=False,
    )
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=c2,
        subject=subject,
        commit=False,
    )

    rows = project_db.execute(block_details_stmt([block_id])).all()

    assert len(rows) == 2
    pairs = {(r.class_id, r.year_id, r.degree_id) for r in rows}
    assert pairs == {
        (c1.id, y1.id, y1.degree_id),
        (c2.id, y2.id, d2.id),
    }


def test_block_details_full_join_chain(project_db: Session) -> None:
    """Every labeled column resolves through the full degree/year/subject/class chain."""
    degree = make_degree(project_db, acronym="LEI", commit=False)
    year = make_year(project_db, degree=degree, number=3, commit=False)
    subject = make_subject(
        project_db,
        year=year,
        acronym="PROG",
        name="Programação",
        commit=False,
    )
    klass = make_class(project_db, year=year, code="3LEI1T", commit=False)
    block_id = uuid.uuid7()
    session_row = make_session(
        project_db,
        week=MONDAY_WEEK,
        weekday=WeekDay.TUESDAY,
        start_time=11,
        duration=3,
        type="TP",
        original_block_id=block_id,
        commit=False,
    )
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=klass,
        subject=subject,
        commit=False,
    )

    rows = project_db.execute(block_details_stmt([block_id])).all()

    assert len(rows) == 1
    (row,) = rows
    assert row.subject_acronym == "PROG"
    assert row.subject_name == "Programação"
    assert row.class_code == "3LEI1T"
    assert row.year == 3
    assert row.degree_acronym == "LEI"
    assert row.weekday == WeekDay.TUESDAY
    assert row.start_time == 11
    assert row.duration == 3
    assert row.session_type == "TP"


def test_block_details_in_restricts_to_requested_ids(project_db: Session) -> None:
    """The ``in_`` filter returns only the requested block ids."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    blocks = []
    for _ in range(3):
        klass = make_class(project_db, year=year, commit=False)
        block_id = uuid.uuid7()
        session_row = make_session(
            project_db,
            week=MONDAY_WEEK,
            original_block_id=block_id,
            commit=False,
        )
        make_session_class_subject(
            project_db,
            session_row=session_row,
            class_row=klass,
            subject=subject,
            commit=False,
        )
        blocks.append(block_id)
    b1, _b2, b3 = blocks

    rows = project_db.execute(block_details_stmt([b1, b3])).all()

    assert {r.original_block_id for r in rows} == {b1, b3}


def test_block_details_empty_and_unknown_id_return_empty(project_db: Session) -> None:
    """Both an empty id list and an unknown id resolve to no rows without error."""
    assert project_db.execute(block_details_stmt([])).all() == []
    assert project_db.execute(block_details_stmt([uuid.uuid7()])).all() == []


def test_block_details_inner_join_excludes_scs_less_session(project_db: Session) -> None:
    """A block whose only session lacks a SessionClassSubject yields no rows."""
    block_id = uuid.uuid7()
    make_session(project_db, original_block_id=block_id, commit=False)

    rows = project_db.execute(block_details_stmt([block_id])).all()

    assert rows == []


def test_block_details_heterogeneous_block_one_row_per_slot(project_db: Session) -> None:
    """A block with two distinct slots yields one detail row per slot."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    klass = make_class(project_db, year=year, commit=False)
    block_id = uuid.uuid7()

    s1 = make_session(
        project_db,
        week=datetime.date(2025, 9, 15),
        weekday=WeekDay.MONDAY,
        start_time=9,
        original_block_id=block_id,
        commit=False,
    )
    make_session_class_subject(
        project_db,
        session_row=s1,
        class_row=klass,
        subject=subject,
        commit=False,
    )
    s2 = make_session(
        project_db,
        week=datetime.date(2025, 9, 22),
        weekday=WeekDay.TUESDAY,
        start_time=14,
        original_block_id=block_id,
        commit=False,
    )
    make_session_class_subject(
        project_db,
        session_row=s2,
        class_row=klass,
        subject=subject,
        commit=False,
    )

    rows = project_db.execute(block_details_stmt([block_id])).all()

    assert len(rows) == 2
    assert {(r.weekday, r.start_time) for r in rows} == {
        (WeekDay.MONDAY, 9),
        (WeekDay.TUESDAY, 14),
    }


def test_block_details_duplicate_ids_do_not_duplicate_output(project_db: Session) -> None:
    """Duplicate ids in the filter do not duplicate the output row."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    klass = make_class(project_db, year=year, commit=False)
    block_id = uuid.uuid7()
    session_row = make_session(
        project_db,
        week=MONDAY_WEEK,
        original_block_id=block_id,
        commit=False,
    )
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=klass,
        subject=subject,
        commit=False,
    )

    rows = project_db.execute(block_details_stmt([block_id, block_id, block_id])).all()

    assert len(rows) == 1
    assert rows[0].original_block_id == block_id


@pytest.mark.parametrize(
    "member",
    [
        WeekDay.MONDAY,
        WeekDay.TUESDAY,
        WeekDay.WEDNESDAY,
        WeekDay.THURSDAY,
        WeekDay.FRIDAY,
        WeekDay.SATURDAY,
    ],
)
def test_block_details_weekday_coerces_to_enum(project_db: Session, member: WeekDay) -> None:
    """Weekday round-trips out of the ``native_enum=False`` column as ``WeekDay``."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    klass = make_class(project_db, year=year, commit=False)
    block_id = uuid.uuid7()
    session_row = make_session(
        project_db,
        week=MONDAY_WEEK,
        weekday=member,
        original_block_id=block_id,
        commit=False,
    )
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=klass,
        subject=subject,
        commit=False,
    )

    rows = project_db.execute(block_details_stmt([block_id])).all()

    assert len(rows) == 1
    assert rows[0].weekday == member
    assert isinstance(rows[0].weekday, WeekDay)


def test_block_details_year_degree_from_class_not_subject_years(project_db: Session) -> None:
    """Year/degree come from the class's year, not the subject's other years."""
    # Subject linked to Y1(D1) and Y2(D2), but the block's class lives in Y1.
    subject = make_subject(project_db, commit=False)
    y1 = subject.years[0]
    d2 = make_degree(project_db, acronym="MEI", commit=False)
    y2 = make_year(project_db, degree=d2, number=2, commit=False)
    _link_subject_to_year(project_db, subject, y2)
    c1 = make_class(project_db, year=y1, commit=False)
    block_id = uuid.uuid7()
    session_row = make_session(
        project_db,
        week=MONDAY_WEEK,
        original_block_id=block_id,
        commit=False,
    )
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=c1,
        subject=subject,
        commit=False,
    )

    rows = project_db.execute(block_details_stmt([block_id])).all()

    assert len(rows) == 1
    (row,) = rows
    assert row.year_id == y1.id
    assert row.year == 1
    assert row.degree_id == y1.degree_id
    # The unrelated second year/degree is absent.
    assert row.year_id != y2.id
    assert row.degree_id != d2.id


# --------------------------------------------------------------------------- #
# block_weeks_stmt
# --------------------------------------------------------------------------- #


def test_block_weeks_min_max_per_block(project_db: Session) -> None:
    """min/max collapse out-of-order bare sessions to first/last week."""
    block_id = uuid.uuid7()
    for week in [
        datetime.date(2025, 9, 1),
        datetime.date(2025, 9, 15),
        datetime.date(2025, 10, 6),
        datetime.date(2025, 12, 1),
    ]:
        make_session(project_db, week=week, original_block_id=block_id, commit=False)

    rows = project_db.execute(block_weeks_stmt([block_id])).all()

    assert len(rows) == 1
    (row,) = rows
    assert row.original_block_id == block_id
    assert row.first_week == datetime.date(2025, 9, 1)
    assert row.last_week == datetime.date(2025, 12, 1)


def test_block_weeks_single_session_first_equals_last(project_db: Session) -> None:
    """A single-session block has equal first and last weeks."""
    block_id = uuid.uuid7()
    make_session(project_db, week=MONDAY_WEEK, original_block_id=block_id, commit=False)

    rows = project_db.execute(block_weeks_stmt([block_id])).all()

    assert len(rows) == 1
    (row,) = rows
    assert row.first_week == MONDAY_WEEK
    assert row.last_week == MONDAY_WEEK


def test_block_weeks_group_by_and_pre_aggregation_filter(project_db: Session) -> None:
    """GROUP BY gives one row per block; filtering happens before aggregation."""
    b1 = uuid.uuid7()
    b2 = uuid.uuid7()
    for week in [datetime.date(2025, 9, 1), datetime.date(2025, 9, 15)]:
        make_session(project_db, week=week, original_block_id=b1, commit=False)
    for week in [
        datetime.date(2025, 10, 6),
        datetime.date(2025, 11, 10),
        datetime.date(2025, 10, 20),
    ]:
        make_session(project_db, week=week, original_block_id=b2, commit=False)

    both = {
        r.original_block_id: (r.first_week, r.last_week)
        for r in project_db.execute(block_weeks_stmt([b1, b2])).all()
    }
    assert both == {
        b1: (datetime.date(2025, 9, 1), datetime.date(2025, 9, 15)),
        b2: (datetime.date(2025, 10, 6), datetime.date(2025, 11, 10)),
    }

    # Querying only B1: B2's wider range must not contaminate the aggregate.
    only_b1 = project_db.execute(block_weeks_stmt([b1])).all()
    assert len(only_b1) == 1
    assert only_b1[0].original_block_id == b1
    assert only_b1[0].first_week == datetime.date(2025, 9, 1)
    assert only_b1[0].last_week == datetime.date(2025, 9, 15)


def test_block_weeks_empty_and_unknown_id_return_empty(project_db: Session) -> None:
    """Empty and unknown filters return no rows (no all-NULL aggregate row)."""
    assert project_db.execute(block_weeks_stmt([])).all() == []
    assert project_db.execute(block_weeks_stmt([uuid.uuid7()])).all() == []


def test_block_weeks_dates_round_trip_as_date(project_db: Session) -> None:
    """Aggregated weeks come back as ``datetime.date`` values."""
    block_id = uuid.uuid7()
    make_session(project_db, week=MONDAY_WEEK, original_block_id=block_id, commit=False)

    rows = project_db.execute(block_weeks_stmt([block_id])).all()

    assert len(rows) == 1
    (row,) = rows
    assert isinstance(row.first_week, datetime.date)
    assert isinstance(row.last_week, datetime.date)
    assert row.first_week == MONDAY_WEEK
    assert row.last_week == MONDAY_WEEK


# --------------------------------------------------------------------------- #
# Cross-statement invariants
# --------------------------------------------------------------------------- #


def test_no_statement_has_implicit_order_by() -> None:
    """None of the three statements emits an ``ORDER BY`` clause."""
    some_ids = [uuid.uuid7()]
    for stmt in (
        candidate_slot_members_stmt(),
        block_details_stmt(some_ids),
        block_weeks_stmt(some_ids),
    ):
        assert "ORDER BY" not in str(stmt)


def test_slot_members_vs_block_details_on_recurring_block(project_db: Session) -> None:
    """slot_members keeps every recurrence; block_details collapses to one row."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    klass = make_class(project_db, year=year, commit=False)
    block_id = uuid.uuid7()
    _attach_block_across_weeks(
        project_db,
        block_id=block_id,
        weeks=[
            datetime.date(2025, 9, 15),
            datetime.date(2025, 9, 22),
            datetime.date(2025, 9, 29),
        ],
        class_row=klass,
        subject=subject,
    )

    slot_rows = project_db.execute(candidate_slot_members_stmt()).all()
    detail_rows = project_db.execute(block_details_stmt([block_id])).all()

    assert len(slot_rows) == 3
    assert {r.original_block_id for r in slot_rows} == {block_id}
    assert len(detail_rows) == 1
    assert detail_rows[0].original_block_id == block_id
