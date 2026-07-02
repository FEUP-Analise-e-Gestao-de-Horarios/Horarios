"""DAO-layer tests for parallel block candidate detection.

These exercise :class:`ParallelBlockCandidateDAO` against a real, seeded
per-project SQLAlchemy SQLite file (the ``project_db`` fixture) and the pure
graph logic in ``parallel_candidate_graph``. They live under ``tests/unit/``
but seed and commit real rows: the DAO is instantiated directly on the seeding
session and its methods are called in-process (no HTTP), so they read the rows
committed by the factories.

The defensive branches in ``get_all_groups_with_info`` (a block whose detail is
missing, a block absent from the weeks map, an edge whose endpoint lacks a
detail) cannot be reached through normal seeding because SQLite has foreign
keys on: every seeded block always has a detail row, a weeks row and consistent
edges. They are therefore driven by monkeypatching the relevant DAO helper to
withhold data for a specific block.
"""

import datetime
import uuid
from uuid import UUID

import pytest
from sqlalchemy.orm import Session

from src.projects.projects_db.dao.parallel_block_candidate_dao import ParallelBlockCandidateDAO
from src.projects.projects_db.dao.parallel_candidate_graph import (
    CandidateComponent,
    _component_uuid,
)
from src.projects.projects_db.models._secondary_tables import subject_years
from src.projects.projects_db.schemas.weekday import WeekDay
from src.projects.views.schemas.parallel_blocks import ParallelCandidateGroupResponse
from tests.factories import (
    make_class,
    make_degree,
    make_group_member,
    make_parallel_candidate_pair,
    make_session,
    make_session_class_subject,
    make_subject,
    make_year,
)

# -- Fixed weeks used throughout ---------------------------------------
W_09_15 = datetime.date(2025, 9, 15)
W_09_22 = datetime.date(2025, 9, 22)
W_09_29 = datetime.date(2025, 9, 29)
W_10_06 = datetime.date(2025, 10, 6)
W_11_03 = datetime.date(2025, 11, 3)


# -- Local seeding helpers ---------------------------------------------
def _seed_block(
    session: Session,
    *,
    subject,
    class_row,
    weeks,
    weekday: WeekDay = WeekDay.MONDAY,
    start_time: int = 9,
    duration: int = 2,
    session_type: str = "T",
    block_id: UUID | None = None,
    commit: bool = False,
) -> UUID:
    """Seed one block: one session per week, all tied to ``class_row``/``subject``.

    Returns the block's ``original_block_id``. All sessions share the same
    ``(weekday, start_time)`` so the block stays *eligible* for candidate
    detection.
    """
    block_id = block_id or uuid.uuid7()
    for week in weeks:
        session_row = make_session(
            session,
            week=week,
            weekday=weekday,
            start_time=start_time,
            duration=duration,
            type=session_type,
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
    if commit:
        session.commit()
    return block_id


def _add_slot_to_block(
    session: Session,
    *,
    block_id: UUID,
    subject,
    class_row,
    week: datetime.date,
    weekday: WeekDay,
    start_time: int,
    commit: bool = False,
) -> None:
    """Attach one extra session (a second slot) to an existing block."""
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
        commit=commit,
    )


def _by_group_id(groups: list) -> dict[UUID, object]:
    return {group.candidate_group_id: group for group in groups}


# ======================================================================
# get_candidate_components
# ======================================================================
def test_get_candidate_components_empty_db(project_db: Session) -> None:
    """An empty per-project DB yields no components."""
    dao = ParallelBlockCandidateDAO(project_db)
    assert dao.get_candidate_components() == []


def test_get_candidate_components_seeded_pair(project_db: Session) -> None:
    """A seeded pair becomes one 2-block component with the expected edge/id."""
    subject = make_subject(project_db, commit=False)
    block_a, block_b = make_parallel_candidate_pair(project_db, subject=subject)

    dao = ParallelBlockCandidateDAO(project_db)
    components = dao.get_candidate_components()

    assert len(components) == 1
    component = components[0]
    assert component.subject_id == subject.id
    assert component.block_ids == frozenset({block_a, block_b})
    assert component.candidate_group_id == _component_uuid(subject.id, {block_a, block_b})

    assert len(component.edges) == 1
    edge = component.edges[0]
    assert (edge.block_a, edge.block_b) == (block_a, block_b)
    assert edge.block_a < edge.block_b
    assert edge.weeks == (W_09_15,)


def test_get_candidate_components_lone_block_yields_nothing(project_db: Session) -> None:
    """A single block with no partner produces no component."""
    subject = make_subject(project_db, commit=False)
    class_row = make_class(project_db, year=subject.years[0], commit=False)
    _seed_block(project_db, subject=subject, class_row=class_row, weeks=[W_09_15])
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    assert dao.get_candidate_components() == []


@pytest.mark.parametrize("with_third_collision", [False, True])
def test_get_candidate_components_drops_heterogeneous_block(
    project_db: Session,
    *,
    with_third_collision: bool,
) -> None:
    """A block spanning two ``(weekday, start_time)`` slots is dropped entirely.

    ``A`` and ``B`` collide MONDAY@9 on w1, but ``A`` also has a second session
    on TUESDAY@10 (w2), making ``A`` heterogeneous. ``A`` is removed from
    candidate detection, leaving ``B`` partnerless, so no component survives.
    When parametrized, ``A`` would also collide with ``C`` on the second slot,
    proving the drop wins even where the second slot forms its own pair.
    """
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    class_a = make_class(project_db, year=year, commit=False)
    class_b = make_class(project_db, year=year, commit=False)

    block_a = _seed_block(project_db, subject=subject, class_row=class_a, weeks=[W_09_15])
    # B is A's would-be partner; the drop of A leaves it alone, so no group forms.
    _seed_block(project_db, subject=subject, class_row=class_b, weeks=[W_09_15])
    _add_slot_to_block(
        project_db,
        block_id=block_a,
        subject=subject,
        class_row=class_a,
        week=W_09_22,
        weekday=WeekDay.TUESDAY,
        start_time=10,
    )
    if with_third_collision:
        class_c = make_class(project_db, year=year, commit=False)
        _seed_block(
            project_db,
            subject=subject,
            class_row=class_c,
            weeks=[W_09_22],
            weekday=WeekDay.TUESDAY,
            start_time=10,
        )
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    components = dao.get_candidate_components()

    # No component survives: the heterogeneous block is dropped, which leaves
    # its partner(s) with nobody to pair with, so both blocks disappear.
    assert components == []


@pytest.mark.parametrize(
    "weeks",
    [
        [W_09_15],
        [W_09_15, W_09_22, W_09_29],
    ],
)
def test_get_candidate_components_multi_week_collision_aggregates(
    project_db: Session,
    weeks: list,
) -> None:
    """Blocks colliding on several weeks share one edge listing all those weeks."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    class_a = make_class(project_db, year=year, commit=False)
    class_b = make_class(project_db, year=year, commit=False)
    block_a = _seed_block(project_db, subject=subject, class_row=class_a, weeks=weeks)
    block_b = _seed_block(project_db, subject=subject, class_row=class_b, weeks=weeks)
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    components = dao.get_candidate_components()

    assert len(components) == 1
    component = components[0]
    assert component.block_ids == frozenset({block_a, block_b})
    assert len(component.edges) == 1
    assert component.edges[0].weeks == tuple(sorted(weeks))


def test_get_candidate_components_block_under_two_subjects(project_db: Session) -> None:
    """A block taught under two subjects appears once per subject component.

    ``A`` has one session carrying two subjects (two classes -> two SCS rows),
    colliding with ``B`` under ``S1`` and ``C`` under ``S2`` on the same slot.
    The union-find is per-subject, so ``A`` is never merged across subjects.
    """
    year = make_year(project_db, commit=False)
    subject1 = make_subject(project_db, year=year, commit=False)
    subject2 = make_subject(project_db, year=year, commit=False)
    class_a1 = make_class(project_db, year=year, commit=False)
    class_a2 = make_class(project_db, year=year, commit=False)
    class_b = make_class(project_db, year=year, commit=False)
    class_c = make_class(project_db, year=year, commit=False)

    block_a = uuid.uuid7()
    session_a = make_session(project_db, week=W_09_15, original_block_id=block_a, commit=False)
    make_session_class_subject(
        project_db,
        session_row=session_a,
        class_row=class_a1,
        subject=subject1,
        commit=False,
    )
    make_session_class_subject(
        project_db,
        session_row=session_a,
        class_row=class_a2,
        subject=subject2,
        commit=False,
    )
    block_b = _seed_block(project_db, subject=subject1, class_row=class_b, weeks=[W_09_15])
    block_c = _seed_block(project_db, subject=subject2, class_row=class_c, weeks=[W_09_15])
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    components = dao.get_candidate_components()

    assert len(components) == 2
    by_subject = {component.subject_id: component for component in components}
    assert by_subject[subject1.id].block_ids == frozenset({block_a, block_b})
    assert by_subject[subject2.id].block_ids == frozenset({block_a, block_c})
    assert by_subject[subject1.id].candidate_group_id != by_subject[subject2.id].candidate_group_id


def test_get_candidate_components_transitive_chain(project_db: Session) -> None:
    """A-B (w1) and B-C (w2) with B at a single slot merge into one 3-block component."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    class_a = make_class(project_db, year=year, commit=False)
    class_b = make_class(project_db, year=year, commit=False)
    class_c = make_class(project_db, year=year, commit=False)

    block_a = _seed_block(project_db, subject=subject, class_row=class_a, weeks=[W_09_15])
    block_b = _seed_block(project_db, subject=subject, class_row=class_b, weeks=[W_09_15, W_09_22])
    block_c = _seed_block(project_db, subject=subject, class_row=class_c, weeks=[W_09_22])
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    components = dao.get_candidate_components()

    assert len(components) == 1
    component = components[0]
    assert component.block_ids == frozenset({block_a, block_b, block_c})

    edge_pairs = {(edge.block_a, edge.block_b): edge.weeks for edge in component.edges}
    ab = tuple(sorted((block_a, block_b)))
    bc = tuple(sorted((block_b, block_c)))
    ac = tuple(sorted((block_a, block_c)))
    assert edge_pairs[ab] == (W_09_15,)
    assert edge_pairs[bc] == (W_09_22,)
    assert ac not in edge_pairs


def test_get_candidate_components_two_independent_pairs(project_db: Session) -> None:
    """Two disjoint pairs of the same subject form two separate components."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    class_a = make_class(project_db, year=year, commit=False)
    class_b = make_class(project_db, year=year, commit=False)
    class_c = make_class(project_db, year=year, commit=False)
    class_d = make_class(project_db, year=year, commit=False)

    block_a = _seed_block(project_db, subject=subject, class_row=class_a, weeks=[W_09_15])
    block_b = _seed_block(project_db, subject=subject, class_row=class_b, weeks=[W_09_15])
    block_c = _seed_block(
        project_db,
        subject=subject,
        class_row=class_c,
        weeks=[W_09_15],
        weekday=WeekDay.TUESDAY,
        start_time=10,
    )
    block_d = _seed_block(
        project_db,
        subject=subject,
        class_row=class_d,
        weeks=[W_09_15],
        weekday=WeekDay.TUESDAY,
        start_time=10,
    )
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    components = dao.get_candidate_components()

    assert len(components) == 2
    memberships = {frozenset(component.block_ids) for component in components}
    assert memberships == {frozenset({block_a, block_b}), frozenset({block_c, block_d})}


def test_get_candidate_components_different_subject_same_slot_no_collide(
    project_db: Session,
) -> None:
    """Two blocks at the same slot but different subjects never collide."""
    year = make_year(project_db, commit=False)
    subject1 = make_subject(project_db, year=year, commit=False)
    subject2 = make_subject(project_db, year=year, commit=False)
    class_a = make_class(project_db, year=year, commit=False)
    class_b = make_class(project_db, year=year, commit=False)
    _seed_block(project_db, subject=subject1, class_row=class_a, weeks=[W_09_15])
    _seed_block(project_db, subject=subject2, class_row=class_b, weeks=[W_09_15])
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    assert dao.get_candidate_components() == []


def test_get_candidate_components_ignores_confirmed_group_state(project_db: Session) -> None:
    """Confirmed-group membership does not change component detection."""
    subject = make_subject(project_db, commit=False)
    block_a, block_b = make_parallel_candidate_pair(project_db, subject=subject, commit=False)
    group_id = uuid.uuid7()
    make_group_member(project_db, group_id=group_id, original_block_id=block_a, commit=False)
    make_group_member(project_db, group_id=group_id, original_block_id=block_b, commit=False)
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    components = dao.get_candidate_components()

    assert len(components) == 1
    assert components[0].block_ids == frozenset({block_a, block_b})


def test_get_candidate_components_group_id_stable_across_calls(project_db: Session) -> None:
    """The candidate_group_id is deterministic across repeated calls."""
    subject = make_subject(project_db, commit=False)
    block_a, block_b = make_parallel_candidate_pair(project_db, subject=subject)

    dao = ParallelBlockCandidateDAO(project_db)
    first = dao.get_candidate_components()
    second = dao.get_candidate_components()

    expected = _component_uuid(subject.id, sorted([block_a, block_b]))
    assert first[0].candidate_group_id == expected
    assert second[0].candidate_group_id == expected


def test_get_candidate_components_adding_third_block_changes_id(project_db: Session) -> None:
    """Growing a component from 2 to 3 blocks changes its candidate_group_id."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    class_a = make_class(project_db, year=year, commit=False)
    class_b = make_class(project_db, year=year, commit=False)
    block_a = _seed_block(project_db, subject=subject, class_row=class_a, weeks=[W_09_15])
    block_b = _seed_block(project_db, subject=subject, class_row=class_b, weeks=[W_09_15])
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    id_two = dao.get_candidate_components()[0].candidate_group_id

    class_c = make_class(project_db, year=year, commit=False)
    block_c = _seed_block(project_db, subject=subject, class_row=class_c, weeks=[W_09_15])
    project_db.commit()

    id_three = dao.get_candidate_components()[0].candidate_group_id

    assert id_two == _component_uuid(subject.id, {block_a, block_b})
    assert id_three == _component_uuid(subject.id, {block_a, block_b, block_c})
    assert id_two != id_three


# ----------------------------------------------------------------------
# The collision key is (week, weekday, start_time, subject) *only*: the slot
# query deliberately omits duration and session_type (they are selected only
# for display in block_details). These lock that in -- blocks sharing a slot
# collide regardless of duration or type, so a future change that folds either
# into the key would fail here instead of silently altering detection.
# ----------------------------------------------------------------------
def test_get_candidate_components_collide_despite_different_duration(
    project_db: Session,
) -> None:
    """Two blocks at the same slot but different durations still form one component."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    class_a = make_class(project_db, year=year, commit=False)
    class_b = make_class(project_db, year=year, commit=False)
    block_a = _seed_block(
        project_db,
        subject=subject,
        class_row=class_a,
        weeks=[W_09_15],
        duration=2,
    )
    block_b = _seed_block(
        project_db,
        subject=subject,
        class_row=class_b,
        weeks=[W_09_15],
        duration=4,
    )
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    components = dao.get_candidate_components()

    assert len(components) == 1
    assert components[0].block_ids == frozenset({block_a, block_b})
    assert components[0].edges[0].weeks == (W_09_15,)


def test_get_candidate_components_collide_despite_different_session_type(
    project_db: Session,
) -> None:
    """A lecture (T) and a lab (P) at the same slot still form one component."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    class_a = make_class(project_db, year=year, commit=False)
    class_b = make_class(project_db, year=year, commit=False)
    block_a = _seed_block(
        project_db,
        subject=subject,
        class_row=class_a,
        weeks=[W_09_15],
        session_type="T",
    )
    block_b = _seed_block(
        project_db,
        subject=subject,
        class_row=class_b,
        weeks=[W_09_15],
        session_type="P",
    )
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    components = dao.get_candidate_components()

    assert len(components) == 1
    assert components[0].block_ids == frozenset({block_a, block_b})


def test_get_candidate_components_block_eligible_despite_varying_duration(
    project_db: Session,
) -> None:
    """A block whose duration varies across weeks keeps one (weekday, start_time)
    slot, so it stays eligible and still partners.

    Eligibility keys on (weekday, start_time) only: block_a runs MONDAY@9 for 2h
    on w1 and 4h on w2 -- one slot, not two -- so it is not dropped as
    heterogeneous and collides with block_b on w1.
    """
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    class_a = make_class(project_db, year=year, commit=False)
    class_b = make_class(project_db, year=year, commit=False)

    block_a = uuid.uuid7()
    _seed_block(
        project_db,
        subject=subject,
        class_row=class_a,
        weeks=[W_09_15],
        duration=2,
        block_id=block_a,
    )
    _seed_block(
        project_db,
        subject=subject,
        class_row=class_a,
        weeks=[W_09_22],
        duration=4,
        block_id=block_a,
    )
    block_b = _seed_block(project_db, subject=subject, class_row=class_b, weeks=[W_09_15])
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    components = dao.get_candidate_components()

    assert len(components) == 1
    assert components[0].block_ids == frozenset({block_a, block_b})
    assert components[0].edges[0].weeks == (W_09_15,)


# ======================================================================
# _block_details
# ======================================================================
def test_block_details_classes_sorted_by_code(project_db: Session) -> None:
    """A block's classes are ordered by code, each with its id and year id."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    class3 = make_class(project_db, year=year, code="C3", commit=False)
    class1 = make_class(project_db, year=year, code="C1", commit=False)
    class2 = make_class(project_db, year=year, code="C2", commit=False)

    block_id = uuid.uuid7()
    session_row = make_session(project_db, week=W_09_15, original_block_id=block_id, commit=False)
    for class_row in (class3, class1, class2):
        make_session_class_subject(
            project_db,
            session_row=session_row,
            class_row=class_row,
            subject=subject,
            commit=False,
        )
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    details, subjects = dao._block_details([block_id])

    detail = details[block_id]
    assert [c.code for c in detail.classes] == ["C1", "C2", "C3"]
    by_code = {c.code: c for c in detail.classes}
    assert by_code["C1"].id == class1.id
    assert by_code["C1"].year_id == year.id
    assert by_code["C2"].id == class2.id
    assert by_code["C3"].id == class3.id

    assert subject.id in subjects
    assert subjects[subject.id].acronym == subject.acronym
    assert subjects[subject.id].name == subject.name
    assert subject.id in detail.year_degrees_by_subject


def test_block_details_distinct_collapses_recurrence(project_db: Session) -> None:
    """Four weekly sessions of one (class, subject) collapse to one class row."""
    subject = make_subject(project_db, commit=False)
    class_row = make_class(project_db, year=subject.years[0], commit=False)
    block_id = _seed_block(
        project_db,
        subject=subject,
        class_row=class_row,
        weeks=[W_09_15, W_09_22, W_09_29, W_10_06],
        session_type="T",
        start_time=9,
        duration=2,
    )
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    details, _ = dao._block_details([block_id])

    detail = details[block_id]
    assert len(detail.classes) == 1
    assert detail.classes[0].id == class_row.id
    assert detail.session_type == "T"
    assert detail.start_time == 9
    assert detail.duration == 2
    assert detail.weekday == WeekDay.MONDAY


def test_block_details_multi_year_degree(project_db: Session) -> None:
    """A subject taught in two year/degree rows lists both in year_degrees_by_subject."""
    degree1 = make_degree(project_db, acronym="D1", commit=False)
    degree2 = make_degree(project_db, acronym="D2", commit=False)
    year1 = make_year(project_db, degree=degree1, number=1, commit=False)
    year2 = make_year(project_db, degree=degree2, number=2, commit=False)
    subject = make_subject(project_db, year=year1, commit=False)
    project_db.execute(
        subject_years.insert().values(subject_id=subject.id, year_id=year2.id),
    )
    class1 = make_class(project_db, year=year1, code="C1", commit=False)
    class2 = make_class(project_db, year=year2, code="C2", commit=False)

    block_id = uuid.uuid7()
    session_row = make_session(project_db, week=W_09_15, original_block_id=block_id, commit=False)
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=class1,
        subject=subject,
        commit=False,
    )
    make_session_class_subject(
        project_db,
        session_row=session_row,
        class_row=class2,
        subject=subject,
        commit=False,
    )
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    details, _ = dao._block_details([block_id])

    detail = details[block_id]
    year_degrees = detail.year_degrees_by_subject[subject.id]
    assert len(year_degrees) == 2
    assert {(yd.year_id, yd.degree_id) for yd in year_degrees} == {
        (year1.id, degree1.id),
        (year2.id, degree2.id),
    }
    assert [c.code for c in detail.classes] == ["C1", "C2"]


def test_block_details_two_blocks_isolated(project_db: Session) -> None:
    """Two blocks yield independent detail entries with no cross-contamination."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    class_a = make_class(project_db, year=year, code="AA", commit=False)
    class_b = make_class(project_db, year=year, code="BB", commit=False)
    block_a = _seed_block(project_db, subject=subject, class_row=class_a, weeks=[W_09_15])
    block_b = _seed_block(project_db, subject=subject, class_row=class_b, weeks=[W_09_15])
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    details, _ = dao._block_details([block_a, block_b])

    assert set(details.keys()) == {block_a, block_b}
    assert [c.id for c in details[block_a].classes] == [class_a.id]
    assert [c.id for c in details[block_b].classes] == [class_b.id]


def test_block_details_unknown_and_empty(project_db: Session) -> None:
    """Unknown ids contribute nothing; an empty request yields two empty maps."""
    subject = make_subject(project_db, commit=False)
    class_row = make_class(project_db, year=subject.years[0], commit=False)
    block_a = _seed_block(project_db, subject=subject, class_row=class_row, weeks=[W_09_15])
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)

    details, _subjects = dao._block_details([block_a, uuid.uuid7()])
    assert set(details.keys()) == {block_a}

    empty_details, empty_subjects = dao._block_details([])
    assert empty_details == {}
    assert empty_subjects == {}


def test_block_details_representative_fields(project_db: Session) -> None:
    """The representative row carries type/start_time/duration/weekday of the block."""
    subject = make_subject(project_db, commit=False)
    class_row = make_class(project_db, year=subject.years[0], commit=False)
    block_id = _seed_block(
        project_db,
        subject=subject,
        class_row=class_row,
        weeks=[W_09_15],
        weekday=WeekDay.WEDNESDAY,
        start_time=14,
        duration=3,
        session_type="TP",
    )
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    details, _ = dao._block_details([block_id])

    detail = details[block_id]
    assert detail.session_type == "TP"
    assert detail.start_time == 14
    assert detail.duration == 3
    assert detail.weekday == WeekDay.WEDNESDAY


# ======================================================================
# _block_weeks
# ======================================================================
def test_block_weeks_min_max_regardless_of_order(project_db: Session) -> None:
    """Weeks reduce to (min, max) irrespective of insertion order."""
    subject = make_subject(project_db, commit=False)
    class_row = make_class(project_db, year=subject.years[0], commit=False)
    block_id = _seed_block(
        project_db,
        subject=subject,
        class_row=class_row,
        weeks=[W_10_06, W_09_15, W_09_29],
    )
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    weeks = dao._block_weeks([block_id])
    assert weeks[block_id] == (W_09_15, W_10_06)


def test_block_weeks_single_and_empty(project_db: Session) -> None:
    """A single-week block gives equal endpoints; unknown ignored; empty -> {}."""
    subject = make_subject(project_db, commit=False)
    class_row = make_class(project_db, year=subject.years[0], commit=False)
    block_id = _seed_block(project_db, subject=subject, class_row=class_row, weeks=[W_09_15])
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)

    weeks = dao._block_weeks([block_id])
    assert weeks[block_id] == (W_09_15, W_09_15)

    mixed = dao._block_weeks([block_id, uuid.uuid7()])
    assert set(mixed.keys()) == {block_id}

    assert dao._block_weeks([]) == {}


def test_block_weeks_multiple_blocks_independent(project_db: Session) -> None:
    """Each block's week range is aggregated independently."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    class_a = make_class(project_db, year=year, commit=False)
    class_b = make_class(project_db, year=year, commit=False)
    block_a = _seed_block(
        project_db,
        subject=subject,
        class_row=class_a,
        weeks=[W_09_15, W_09_22],
    )
    block_b = _seed_block(
        project_db,
        subject=subject,
        class_row=class_b,
        weeks=[W_10_06, W_11_03],
    )
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    weeks = dao._block_weeks([block_a, block_b])
    assert weeks[block_a] == (W_09_15, W_09_22)
    assert weeks[block_b] == (W_10_06, W_11_03)


# ======================================================================
# _confirmed_group_by_block
# ======================================================================
def test_confirmed_group_by_block_scoped(project_db: Session) -> None:
    """Only queried blocks with a membership row are returned; scope is respected."""
    group1 = uuid.uuid7()
    block_a = uuid.uuid7()
    block_b = uuid.uuid7()
    block_c = uuid.uuid7()
    block_z = uuid.uuid7()
    make_group_member(project_db, group_id=group1, original_block_id=block_a, commit=False)
    make_group_member(project_db, group_id=group1, original_block_id=block_b, commit=False)
    make_group_member(project_db, group_id=uuid.uuid7(), original_block_id=block_z, commit=False)
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)

    result = dao._confirmed_group_by_block([block_a, block_b, block_c])
    assert result == {block_a: group1, block_b: group1}
    assert block_c not in result
    assert block_z not in result

    assert dao._confirmed_group_by_block([block_a]) == {block_a: group1}
    assert dao._confirmed_group_by_block([]) == {}


def test_confirmed_group_by_block_distinct_groups(project_db: Session) -> None:
    """Blocks in different confirmed groups map to their respective group ids."""
    group1 = uuid.uuid7()
    group2 = uuid.uuid7()
    block_a = uuid.uuid7()
    block_b = uuid.uuid7()
    make_group_member(project_db, group_id=group1, original_block_id=block_a, commit=False)
    make_group_member(project_db, group_id=group2, original_block_id=block_b, commit=False)
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    assert dao._confirmed_group_by_block([block_a, block_b]) == {
        block_a: group1,
        block_b: group2,
    }


# ======================================================================
# get_all_groups_with_info
# ======================================================================
def test_get_all_groups_with_info_empty_db(project_db: Session) -> None:
    """An empty DB short-circuits to []."""
    dao = ParallelBlockCandidateDAO(project_db)
    assert dao.get_all_groups_with_info() == []


def test_get_all_groups_with_info_pair_fully_populated(project_db: Session) -> None:
    """A 2-block pair renders one fully-populated group."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    degree = year.degree
    block_a, block_b = make_parallel_candidate_pair(project_db, subject=subject)

    dao = ParallelBlockCandidateDAO(project_db)
    groups = dao.get_all_groups_with_info()

    assert len(groups) == 1
    group = groups[0]
    assert group.candidate_group_id == _component_uuid(subject.id, {block_a, block_b})
    assert group.weekday == WeekDay.MONDAY

    node_ids = [node.original_block_id for node in group.nodes]
    assert node_ids == sorted([block_a, block_b])
    for node in group.nodes:
        assert node.confirmed_group_id is None
        assert node.session.type == "T"
        assert node.session.start_time == 9
        assert node.session.duration == 2
        assert node.first_week == W_09_15
        assert node.last_week == W_09_15
        assert len(node.classes) == 1

    assert group.subject.id == subject.id
    assert len(group.subject.years) == 1
    assert group.subject.years[0].id == year.id
    assert group.subject.years[0].degree.id == degree.id

    assert len(group.edges) == 1
    edge = group.edges[0]
    assert edge.source < edge.target
    assert {edge.source, edge.target} == {block_a, block_b}
    assert edge.weeks == [W_09_15]


def test_get_all_groups_with_info_nodes_sorted_by_id(project_db: Session) -> None:
    """Nodes are emitted in ascending original_block_id order."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    id1 = UUID(int=1)
    id2 = UUID(int=2)
    id3 = UUID(int=3)
    # Insert deliberately out of order.
    for block_id in (id3, id1, id2):
        class_row = make_class(project_db, year=year, commit=False)
        _seed_block(
            project_db,
            subject=subject,
            class_row=class_row,
            weeks=[W_09_15],
            block_id=block_id,
        )
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    groups = dao.get_all_groups_with_info()

    assert len(groups) == 1
    node_ids = [node.original_block_id for node in groups[0].nodes]
    assert node_ids == [id1, id2, id3]


def test_get_all_groups_with_info_missing_detail_drops_component(
    project_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A component with only one valid node (detail withheld) is dropped."""
    subject = make_subject(project_db, commit=False)
    block_a, block_b = make_parallel_candidate_pair(project_db, subject=subject)

    dao = ParallelBlockCandidateDAO(project_db)
    real_details = dao._block_details

    # Keep only the lowest id (the representative) so exactly one node survives.
    keeper = min(block_a, block_b)

    def only_one(block_ids):
        details, subjects = real_details(block_ids)
        return {k: v for k, v in details.items() if k == keeper}, subjects

    monkeypatch.setattr(dao, "_block_details", only_one)

    assert dao.get_all_groups_with_info() == []


def test_get_all_groups_with_info_missing_detail_skips_node(
    project_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """In a 3-block component, a block whose detail is withheld is skipped."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    ids = [UUID(int=1), UUID(int=2), UUID(int=3)]
    for block_id in ids:
        class_row = make_class(project_db, year=year, commit=False)
        _seed_block(
            project_db,
            subject=subject,
            class_row=class_row,
            weeks=[W_09_15],
            block_id=block_id,
        )
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    real_details = dao._block_details
    dropped = ids[2]  # non-representative, not nodes[0]

    def omit_third(block_ids):
        details, subjects = real_details(block_ids)
        return {k: v for k, v in details.items() if k != dropped}, subjects

    monkeypatch.setattr(dao, "_block_details", omit_third)

    groups = dao.get_all_groups_with_info()
    assert len(groups) == 1
    node_ids = [node.original_block_id for node in groups[0].nodes]
    assert node_ids == [ids[0], ids[1]]
    assert dropped not in node_ids


@pytest.mark.parametrize("block_count", [3, 2])
def test_get_all_groups_with_info_missing_weeks(
    project_db: Session,
    monkeypatch: pytest.MonkeyPatch,
    block_count: int,
) -> None:
    """Blocks absent from the weeks map are skipped (3-block keeps 2; 2-block -> [])."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    ids = [UUID(int=i) for i in range(1, block_count + 1)]
    for block_id in ids:
        class_row = make_class(project_db, year=year, commit=False)
        _seed_block(
            project_db,
            subject=subject,
            class_row=class_row,
            weeks=[W_09_15],
            block_id=block_id,
        )
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    real_weeks = dao._block_weeks
    dropped = ids[-1]

    def omit_one(block_ids):
        return {k: v for k, v in real_weeks(block_ids).items() if k != dropped}

    monkeypatch.setattr(dao, "_block_weeks", omit_one)

    groups = dao.get_all_groups_with_info()
    if block_count == 3:
        assert len(groups) == 1
        node_ids = [node.original_block_id for node in groups[0].nodes]
        assert node_ids == [ids[0], ids[1]]
        assert dropped not in node_ids
    else:
        assert groups == []


def test_get_all_groups_with_info_years_dedup_same_year(project_db: Session) -> None:
    """When both blocks' classes are in the same year, subject.years has one entry."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    class_a = make_class(project_db, year=year, commit=False)
    class_b = make_class(project_db, year=year, commit=False)
    _seed_block(project_db, subject=subject, class_row=class_a, weeks=[W_09_15])
    _seed_block(project_db, subject=subject, class_row=class_b, weeks=[W_09_15])
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    groups = dao.get_all_groups_with_info()

    assert len(groups) == 1
    assert len(groups[0].subject.years) == 1
    assert groups[0].subject.years[0].id == year.id


def test_get_all_groups_with_info_years_distinct_from_nodes(project_db: Session) -> None:
    """Two blocks in different years of one subject contribute both years."""
    degree = make_degree(project_db, commit=False)
    year1 = make_year(project_db, degree=degree, number=1, commit=False)
    year2 = make_year(project_db, degree=degree, number=2, commit=False)
    subject = make_subject(project_db, year=year1, commit=False)
    project_db.execute(
        subject_years.insert().values(subject_id=subject.id, year_id=year2.id),
    )
    class_a = make_class(project_db, year=year1, commit=False)
    class_b = make_class(project_db, year=year2, commit=False)
    _seed_block(project_db, subject=subject, class_row=class_a, weeks=[W_09_15])
    _seed_block(project_db, subject=subject, class_row=class_b, weeks=[W_09_15])
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    groups = dao.get_all_groups_with_info()

    assert len(groups) == 1
    years = groups[0].subject.years
    assert {y.id for y in years} == {year1.id, year2.id}
    for y in years:
        assert y.degree.id == degree.id


def test_get_all_groups_with_info_years_ordered_with_dedup(
    project_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """subject.years sorts by (year_number, degree_acronym) and dedups by year_id."""
    from src.projects.projects_db.dao import parallel_block_candidate_dao as dao_module

    subject = make_subject(project_db, commit=False)
    block_a, block_b = make_parallel_candidate_pair(project_db, subject=subject)

    dao = ParallelBlockCandidateDAO(project_db)
    real_details = dao._block_details

    year_bbb = UUID(int=1001)
    year_zzz = UUID(int=1002)
    year_aaa = UUID(int=1003)
    yd_bbb = dao_module._YearDegree(
        year_id=year_bbb,
        year_number=2,
        degree_id=UUID(int=2001),
        degree_acronym="BBB",
        degree_name="Degree BBB",
    )
    yd_zzz = dao_module._YearDegree(
        year_id=year_zzz,
        year_number=1,
        degree_id=UUID(int=2002),
        degree_acronym="ZZZ",
        degree_name="Degree ZZZ",
    )
    yd_aaa = dao_module._YearDegree(
        year_id=year_aaa,
        year_number=2,
        degree_id=UUID(int=2003),
        degree_acronym="AAA",
        degree_name="Degree AAA",
    )
    lowest = min(block_a, block_b)

    def rich_details(block_ids):
        details, subjects = real_details(block_ids)
        patched = {}
        for block_id, detail in details.items():
            if block_id == lowest:
                extra = (yd_bbb, yd_zzz, yd_aaa)
            else:
                # Duplicate year_id (yd_bbb) on the other node to prove dedup.
                extra = (yd_bbb,)
            patched[block_id] = dao_module._BlockDetail(
                classes=detail.classes,
                session_type=detail.session_type,
                start_time=detail.start_time,
                duration=detail.duration,
                weekday=detail.weekday,
                year_degrees_by_subject={subject.id: extra},
            )
        return patched, subjects

    monkeypatch.setattr(dao, "_block_details", rich_details)

    groups = dao.get_all_groups_with_info()
    assert len(groups) == 1
    year_ids = [y.id for y in groups[0].subject.years]
    # Sorted by (year_number, degree_acronym): (1,ZZZ) < (2,AAA) < (2,BBB).
    assert year_ids == [year_zzz, year_aaa, year_bbb]
    # Both nodes contribute yd_bbb; the DAO must dedup it to a single row.
    assert year_ids.count(year_bbb) == 1


def test_get_all_groups_with_info_years_scoped_to_subject(project_db: Session) -> None:
    """Only the component subject's year rows appear; the other subject's are excluded."""
    year1 = make_year(project_db, number=1, commit=False)
    year2 = make_year(project_db, degree=year1.degree, number=2, commit=False)
    subject1 = make_subject(project_db, year=year1, commit=False)
    subject2 = make_subject(project_db, year=year2, commit=False)
    class1 = make_class(project_db, year=year1, commit=False)
    class2 = make_class(project_db, year=year2, commit=False)
    class_b = make_class(project_db, year=year1, commit=False)

    # block_a carries two SCS: (class1/S1) and (class2/S2).
    block_a = uuid.uuid7()
    session_a = make_session(project_db, week=W_09_15, original_block_id=block_a, commit=False)
    make_session_class_subject(
        project_db,
        session_row=session_a,
        class_row=class1,
        subject=subject1,
        commit=False,
    )
    make_session_class_subject(
        project_db,
        session_row=session_a,
        class_row=class2,
        subject=subject2,
        commit=False,
    )
    # block_b shares the S1 slot, forming an S1 component with block_a.
    _seed_block(project_db, subject=subject1, class_row=class_b, weeks=[W_09_15])
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    groups = dao.get_all_groups_with_info()

    s1_groups = [g for g in groups if g.subject.id == subject1.id]
    assert len(s1_groups) == 1
    years = s1_groups[0].subject.years
    assert {y.id for y in years} == {year1.id}


def test_get_all_groups_with_info_confirmed_pair(project_db: Session) -> None:
    """A confirmed pair carries the same confirmed_group_id on both nodes."""
    subject = make_subject(project_db, commit=False)
    block_a, block_b = make_parallel_candidate_pair(project_db, subject=subject, commit=False)
    group_id = uuid.uuid7()
    make_group_member(project_db, group_id=group_id, original_block_id=block_a, commit=False)
    make_group_member(project_db, group_id=group_id, original_block_id=block_b, commit=False)
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    groups = dao.get_all_groups_with_info()

    assert len(groups) == 1
    for node in groups[0].nodes:
        assert node.confirmed_group_id == group_id


def test_get_all_groups_with_info_confirmed_partial(project_db: Session) -> None:
    """A 3-block component with only A,B confirmed leaves C unconfirmed, none dropped."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    ids = [UUID(int=1), UUID(int=2), UUID(int=3)]
    for block_id in ids:
        class_row = make_class(project_db, year=year, commit=False)
        _seed_block(
            project_db,
            subject=subject,
            class_row=class_row,
            weeks=[W_09_15],
            block_id=block_id,
        )
    group_id = uuid.uuid7()
    make_group_member(project_db, group_id=group_id, original_block_id=ids[0], commit=False)
    make_group_member(project_db, group_id=group_id, original_block_id=ids[1], commit=False)
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    groups = dao.get_all_groups_with_info()

    assert len(groups) == 1
    by_id = {node.original_block_id: node for node in groups[0].nodes}
    assert set(by_id.keys()) == set(ids)
    assert by_id[ids[0]].confirmed_group_id == group_id
    assert by_id[ids[1]].confirmed_group_id == group_id
    assert by_id[ids[2]].confirmed_group_id is None


def test_get_all_groups_with_info_confirmed_multi_group(project_db: Session) -> None:
    """A 4-block component with A,B under G1 and C,D under G2 keeps per-block ids."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    ids = [UUID(int=1), UUID(int=2), UUID(int=3), UUID(int=4)]
    for block_id in ids:
        class_row = make_class(project_db, year=year, commit=False)
        _seed_block(
            project_db,
            subject=subject,
            class_row=class_row,
            weeks=[W_09_15],
            block_id=block_id,
        )
    group1 = uuid.uuid7()
    group2 = uuid.uuid7()
    make_group_member(project_db, group_id=group1, original_block_id=ids[0], commit=False)
    make_group_member(project_db, group_id=group1, original_block_id=ids[1], commit=False)
    make_group_member(project_db, group_id=group2, original_block_id=ids[2], commit=False)
    make_group_member(project_db, group_id=group2, original_block_id=ids[3], commit=False)
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    groups = dao.get_all_groups_with_info()

    assert len(groups) == 1
    by_id = {node.original_block_id: node for node in groups[0].nodes}
    assert set(by_id.keys()) == set(ids)
    assert by_id[ids[0]].confirmed_group_id == group1
    assert by_id[ids[1]].confirmed_group_id == group1
    assert by_id[ids[2]].confirmed_group_id == group2
    assert by_id[ids[3]].confirmed_group_id == group2


def test_get_all_groups_with_info_edges_filtered_when_endpoint_missing(
    project_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Edges touching a detail-less endpoint drop; the group survives (no reconnect check)."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    # Path topology a--c--b: c is the sole connector. a collides with c only on
    # W_09_15 and b collides with c only on W_09_22, so a and b never share a
    # slot and have no direct edge -- the union is purely transitive through c.
    id_a = UUID(int=1)
    id_b = UUID(int=2)
    id_c = UUID(int=3)
    class_a = make_class(project_db, year=year, commit=False)
    class_b = make_class(project_db, year=year, commit=False)
    class_c = make_class(project_db, year=year, commit=False)
    _seed_block(project_db, subject=subject, class_row=class_a, weeks=[W_09_15], block_id=id_a)
    _seed_block(project_db, subject=subject, class_row=class_b, weeks=[W_09_22], block_id=id_b)
    _seed_block(
        project_db,
        subject=subject,
        class_row=class_c,
        weeks=[W_09_15, W_09_22],
        block_id=id_c,
    )
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    real_details = dao._block_details

    def omit_c(block_ids):
        details, subjects = real_details(block_ids)
        return {k: v for k, v in details.items() if k != id_c}, subjects

    monkeypatch.setattr(dao, "_block_details", omit_c)

    groups = dao.get_all_groups_with_info()
    assert len(groups) == 1
    group = groups[0]
    node_ids = [node.original_block_id for node in group.nodes]
    assert node_ids == [id_a, id_b]
    assert id_c not in node_ids
    # Both original edges (a,c) and (c,b) touched c and are dropped, leaving a
    # and b with no edge between them. The group still survives with both nodes:
    # dropping a connector does not trigger a re-check that the remainder is
    # still connected.
    assert group.edges == []


def test_get_all_groups_with_info_edges_partially_filtered(
    project_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only edges touching a detail-less block drop; unrelated edges survive.

    Triangle {a,b,c} on W_09_15 (edges a-b, a-c, b-c) plus a connector c-d on
    W_09_22. Withholding d's detail drops node d and the single c-d edge, while
    the three triangle edges -- none of which touch d -- must remain. This is
    the mixed case: some edges filtered, some retained in one group.
    """
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    id_a = UUID(int=1)
    id_b = UUID(int=2)
    id_c = UUID(int=3)
    id_d = UUID(int=4)
    class_a = make_class(project_db, year=year, commit=False)
    class_b = make_class(project_db, year=year, commit=False)
    class_c = make_class(project_db, year=year, commit=False)
    class_d = make_class(project_db, year=year, commit=False)
    _seed_block(project_db, subject=subject, class_row=class_a, weeks=[W_09_15], block_id=id_a)
    _seed_block(project_db, subject=subject, class_row=class_b, weeks=[W_09_15], block_id=id_b)
    _seed_block(
        project_db,
        subject=subject,
        class_row=class_c,
        weeks=[W_09_15, W_09_22],
        block_id=id_c,
    )
    _seed_block(project_db, subject=subject, class_row=class_d, weeks=[W_09_22], block_id=id_d)
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    real_details = dao._block_details

    def omit_d(block_ids):
        details, subjects = real_details(block_ids)
        return {k: v for k, v in details.items() if k != id_d}, subjects

    monkeypatch.setattr(dao, "_block_details", omit_d)

    groups = dao.get_all_groups_with_info()
    assert len(groups) == 1
    group = groups[0]
    node_ids = [node.original_block_id for node in group.nodes]
    assert node_ids == [id_a, id_b, id_c]
    assert id_d not in node_ids

    edge_pairs = {(edge.source, edge.target) for edge in group.edges}
    assert edge_pairs == {(id_a, id_b), (id_a, id_c), (id_b, id_c)}
    # The c-d connector touched the withheld block and is gone; the triangle stays.
    assert all(id_d not in pair for pair in edge_pairs)


def test_get_all_groups_with_info_representative_weekday(project_db: Session) -> None:
    """The group's weekday comes from the lowest-id node's session."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    class_a = make_class(project_db, year=year, commit=False)
    class_b = make_class(project_db, year=year, commit=False)
    _seed_block(
        project_db,
        subject=subject,
        class_row=class_a,
        weeks=[W_09_15],
        weekday=WeekDay.WEDNESDAY,
        start_time=14,
    )
    _seed_block(
        project_db,
        subject=subject,
        class_row=class_b,
        weeks=[W_09_15],
        weekday=WeekDay.WEDNESDAY,
        start_time=14,
    )
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    groups = dao.get_all_groups_with_info()

    assert len(groups) == 1
    assert groups[0].weekday == WeekDay.WEDNESDAY


def test_get_all_groups_with_info_multiple_components(project_db: Session) -> None:
    """Two independent components with distinct subjects render as two groups."""
    year = make_year(project_db, commit=False)
    subject1 = make_subject(project_db, year=year, commit=False)
    subject2 = make_subject(project_db, year=year, commit=False)
    a1, a2 = make_parallel_candidate_pair(project_db, subject=subject1, commit=False)
    b1, b2 = make_parallel_candidate_pair(
        project_db,
        subject=subject2,
        weekday=WeekDay.TUESDAY,
        start_time=10,
        commit=False,
    )
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    groups = dao.get_all_groups_with_info()

    assert len(groups) == 2
    by_id = _by_group_id(groups)
    assert set(by_id.keys()) == {
        _component_uuid(subject1.id, {a1, a2}),
        _component_uuid(subject2.id, {b1, b2}),
    }


def test_get_all_groups_with_info_same_blocks_two_subjects(project_db: Session) -> None:
    """Two blocks colliding under two subjects render as two groups, distinct ids."""
    year = make_year(project_db, commit=False)
    subject1 = make_subject(project_db, year=year, commit=False)
    subject2 = make_subject(project_db, year=year, commit=False)
    class_a1 = make_class(project_db, year=year, commit=False)
    class_a2 = make_class(project_db, year=year, commit=False)
    class_b1 = make_class(project_db, year=year, commit=False)
    class_b2 = make_class(project_db, year=year, commit=False)

    block_a = UUID(int=1)
    block_b = UUID(int=2)
    session_a = make_session(project_db, week=W_09_15, original_block_id=block_a, commit=False)
    make_session_class_subject(
        project_db,
        session_row=session_a,
        class_row=class_a1,
        subject=subject1,
        commit=False,
    )
    make_session_class_subject(
        project_db,
        session_row=session_a,
        class_row=class_a2,
        subject=subject2,
        commit=False,
    )
    session_b = make_session(project_db, week=W_09_15, original_block_id=block_b, commit=False)
    make_session_class_subject(
        project_db,
        session_row=session_b,
        class_row=class_b1,
        subject=subject1,
        commit=False,
    )
    make_session_class_subject(
        project_db,
        session_row=session_b,
        class_row=class_b2,
        subject=subject2,
        commit=False,
    )
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    groups = dao.get_all_groups_with_info()

    assert len(groups) == 2
    subjects_seen = {g.subject.id for g in groups}
    assert subjects_seen == {subject1.id, subject2.id}
    ids_seen = {g.candidate_group_id for g in groups}
    assert len(ids_seen) == 2
    for group in groups:
        node_ids = {node.original_block_id for node in group.nodes}
        assert node_ids == {block_a, block_b}


def test_get_all_groups_with_info_heterogeneous_block_never_node(project_db: Session) -> None:
    """A heterogeneous block is never a node; the remaining pair is a group."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    class_a = make_class(project_db, year=year, commit=False)
    class_b = make_class(project_db, year=year, commit=False)
    class_c = make_class(project_db, year=year, commit=False)

    block_a = _seed_block(project_db, subject=subject, class_row=class_a, weeks=[W_09_15])
    _add_slot_to_block(
        project_db,
        block_id=block_a,
        subject=subject,
        class_row=class_a,
        week=W_09_22,
        weekday=WeekDay.TUESDAY,
        start_time=9,
    )
    block_b = _seed_block(project_db, subject=subject, class_row=class_b, weeks=[W_09_15])
    block_c = _seed_block(project_db, subject=subject, class_row=class_c, weeks=[W_09_15])
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    groups = dao.get_all_groups_with_info()

    assert len(groups) == 1
    node_ids = {node.original_block_id for node in groups[0].nodes}
    assert node_ids == {block_b, block_c}
    assert block_a not in node_ids


def test_get_all_groups_with_info_first_last_week(project_db: Session) -> None:
    """A node's first/last week are the min/max of its sessions' weeks."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    class_a = make_class(project_db, year=year, commit=False)
    class_b = make_class(project_db, year=year, commit=False)
    block_a = _seed_block(
        project_db,
        subject=subject,
        class_row=class_a,
        weeks=[W_09_15, W_09_22, W_09_29],
    )
    _seed_block(project_db, subject=subject, class_row=class_b, weeks=[W_09_15])
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    groups = dao.get_all_groups_with_info()

    assert len(groups) == 1
    by_id = {node.original_block_id: node for node in groups[0].nodes}
    assert by_id[block_a].first_week == W_09_15
    assert by_id[block_a].last_week == W_09_29


def test_get_all_groups_with_info_class_year_id_matches_class(project_db: Session) -> None:
    """Each rendered class carries the year_id of its own class."""
    degree = make_degree(project_db, commit=False)
    year1 = make_year(project_db, degree=degree, number=1, commit=False)
    year2 = make_year(project_db, degree=degree, number=2, commit=False)
    subject = make_subject(project_db, year=year1, commit=False)
    project_db.execute(
        subject_years.insert().values(subject_id=subject.id, year_id=year2.id),
    )
    class1 = make_class(project_db, year=year1, code="C1", commit=False)
    class2 = make_class(project_db, year=year2, code="C2", commit=False)

    # Block B has two classes in different years; pair it with a partner block.
    block_b = UUID(int=2)
    session_b = make_session(project_db, week=W_09_15, original_block_id=block_b, commit=False)
    make_session_class_subject(
        project_db,
        session_row=session_b,
        class_row=class1,
        subject=subject,
        commit=False,
    )
    make_session_class_subject(
        project_db,
        session_row=session_b,
        class_row=class2,
        subject=subject,
        commit=False,
    )
    partner_class = make_class(project_db, year=year1, code="CP", commit=False)
    _seed_block(
        project_db,
        subject=subject,
        class_row=partner_class,
        weeks=[W_09_15],
        block_id=UUID(int=1),
    )
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    groups = dao.get_all_groups_with_info()

    assert len(groups) == 1
    by_id = {node.original_block_id: node for node in groups[0].nodes}
    by_code = {c.code: c for c in by_id[block_b].classes}
    assert by_code["C1"].year_id == year1.id
    assert by_code["C2"].year_id == year2.id


def test_get_all_groups_with_info_edge_weeks_sorted(project_db: Session) -> None:
    """A single edge's weeks are returned as a sorted date list; source<target."""
    subject = make_subject(project_db, commit=False)
    year = subject.years[0]
    class_a = make_class(project_db, year=year, commit=False)
    class_b = make_class(project_db, year=year, commit=False)
    # Insert weeks out of order (09-29 before 09-15).
    block_a = _seed_block(project_db, subject=subject, class_row=class_a, weeks=[W_09_29, W_09_15])
    block_b = _seed_block(project_db, subject=subject, class_row=class_b, weeks=[W_09_29, W_09_15])
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    groups = dao.get_all_groups_with_info()

    assert len(groups) == 1
    assert len(groups[0].edges) == 1
    edge = groups[0].edges[0]
    assert edge.source < edge.target
    assert {edge.source, edge.target} == {block_a, block_b}
    assert edge.weeks == [W_09_15, W_09_29]


def test_get_all_groups_with_info_all_block_ids_dedup(project_db: Session) -> None:
    """Blocks shared by two subject components are deduped yet render per subject."""
    year1 = make_year(project_db, number=1, commit=False)
    year2 = make_year(project_db, degree=year1.degree, number=2, commit=False)
    subject1 = make_subject(project_db, year=year1, commit=False)
    subject2 = make_subject(project_db, year=year2, commit=False)
    class_a1 = make_class(project_db, year=year1, commit=False)
    class_a2 = make_class(project_db, year=year2, commit=False)
    class_b1 = make_class(project_db, year=year1, commit=False)
    class_b2 = make_class(project_db, year=year2, commit=False)

    block_a = UUID(int=1)
    block_b = UUID(int=2)
    session_a = make_session(project_db, week=W_09_15, original_block_id=block_a, commit=False)
    make_session_class_subject(
        project_db,
        session_row=session_a,
        class_row=class_a1,
        subject=subject1,
        commit=False,
    )
    make_session_class_subject(
        project_db,
        session_row=session_a,
        class_row=class_a2,
        subject=subject2,
        commit=False,
    )
    session_b = make_session(project_db, week=W_09_15, original_block_id=block_b, commit=False)
    make_session_class_subject(
        project_db,
        session_row=session_b,
        class_row=class_b1,
        subject=subject1,
        commit=False,
    )
    make_session_class_subject(
        project_db,
        session_row=session_b,
        class_row=class_b2,
        subject=subject2,
        commit=False,
    )
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    groups = dao.get_all_groups_with_info()

    assert len(groups) == 2
    by_subject = {g.subject.id: g for g in groups}
    assert {y.id for y in by_subject[subject1.id].subject.years} == {year1.id}
    assert {y.id for y in by_subject[subject2.id].subject.years} == {year2.id}
    for group in groups:
        node_ids = {node.original_block_id for node in group.nodes}
        assert node_ids == {block_a, block_b}


def test_get_all_groups_with_info_validates_against_response_schema(project_db: Session) -> None:
    """Every rendered group validates against ParallelCandidateGroupResponse."""
    degree = make_degree(project_db, commit=False)
    year1 = make_year(project_db, degree=degree, number=1, commit=False)
    year2 = make_year(project_db, degree=degree, number=2, commit=False)
    subject = make_subject(project_db, year=year1, commit=False)
    project_db.execute(
        subject_years.insert().values(subject_id=subject.id, year_id=year2.id),
    )
    ids = [UUID(int=1), UUID(int=2), UUID(int=3)]
    class_a = make_class(project_db, year=year1, code="AA", commit=False)
    class_b = make_class(project_db, year=year2, code="BB", commit=False)
    class_c = make_class(project_db, year=year1, code="CC", commit=False)
    for block_id, class_row in zip(ids, (class_a, class_b, class_c), strict=True):
        _seed_block(
            project_db,
            subject=subject,
            class_row=class_row,
            weeks=[W_09_15, W_09_22],
            block_id=block_id,
        )
    group_id = uuid.uuid7()
    make_group_member(project_db, group_id=group_id, original_block_id=ids[0], commit=False)
    make_group_member(project_db, group_id=group_id, original_block_id=ids[1], commit=False)
    project_db.commit()

    dao = ParallelBlockCandidateDAO(project_db)
    groups = dao.get_all_groups_with_info()

    assert len(groups) == 1
    for group in groups:
        validated = ParallelCandidateGroupResponse.model_validate(group)
        assert validated.candidate_group_id == group.candidate_group_id
        assert {y.id for y in validated.subject.years} == {year1.id, year2.id}


def test_get_all_groups_with_info_synthetic_single_node_dropped(
    project_db: Session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A synthetic single-node component is dropped even with details/weeks present."""
    from src.projects.projects_db.dao import parallel_block_candidate_dao as dao_module

    subject = make_subject(project_db, commit=False)
    project_db.commit()

    single_id = UUID(int=42)
    component = CandidateComponent(
        candidate_group_id=_component_uuid(subject.id, {single_id}),
        subject_id=subject.id,
        block_ids=frozenset({single_id}),
        edges=(),
    )

    detail = dao_module._BlockDetail(
        classes=[],
        session_type="T",
        start_time=9,
        duration=2,
        weekday=WeekDay.MONDAY,
        year_degrees_by_subject={
            subject.id: (
                dao_module._YearDegree(
                    year_id=UUID(int=100),
                    year_number=1,
                    degree_id=UUID(int=200),
                    degree_acronym="D",
                    degree_name="Degree D",
                ),
            ),
        },
    )
    subject_info = dao_module._SubjectInfo(acronym=subject.acronym, name=subject.name)

    dao = ParallelBlockCandidateDAO(project_db)
    monkeypatch.setattr(dao, "get_candidate_components", lambda: [component])
    monkeypatch.setattr(
        dao,
        "_block_details",
        lambda block_ids: ({single_id: detail}, {subject.id: subject_info}),
    )
    monkeypatch.setattr(dao, "_block_weeks", lambda block_ids: {single_id: (W_09_15, W_09_15)})
    monkeypatch.setattr(dao, "_confirmed_group_by_block", lambda block_ids: {})

    assert dao.get_all_groups_with_info() == []
