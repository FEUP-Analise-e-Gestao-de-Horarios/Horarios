"""DAO-level tests for :class:`ParallelBlockGroupDAO` and the
``ParallelBlockGroupMember`` constraints.

These run against a real, seeded per-project SQLAlchemy SQLite file (the
``project_db`` fixture provisions it and yields a live ``Session``). The DAO is
instantiated directly on that session; no HTTP is involved.

Key invariants exercised here:

* ``create`` / ``clear_all`` **never commit** — they only stage work on the
  session. Reads within the same session see the staged rows thanks to
  autoflush; a ``rollback`` discards them and restores pre-existing committed
  rows.
* ``ParallelBlockGroupMember`` has a composite PK and a UNIQUE constraint on
  ``original_block_id`` (FK/UNIQUE enforcement is on via the WAL/pragma setup).
"""

import uuid

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.projects.projects_db.dao.parallel_block_group_dao import ParallelBlockGroupDAO
from src.projects.projects_db.models import ParallelBlockGroupMember
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session
from tests.factories import make_group_member


def _members(session) -> list[ParallelBlockGroupMember]:
    """All membership rows currently visible in ``session`` (autoflush on)."""
    return list(session.scalars(select(ParallelBlockGroupMember)).all())


def _block_ids(session) -> set:
    """The set of ``original_block_id`` values currently visible."""
    return {m.original_block_id for m in _members(session)}


def _blocks_for_group(session, group_id) -> set:
    """The set of ``original_block_id`` values staged/committed for a group."""
    return {m.original_block_id for m in _members(session) if m.parallel_block_group_id == group_id}


# ---------------------------------------------------------------------------
# -- create
# ---------------------------------------------------------------------------


def test_create_happy_path_returns_uuid7_one_row_per_member(project_db) -> None:
    """create([a, b]) mints a uuid7 group and stages exactly two member rows."""
    dao = ParallelBlockGroupDAO(project_db)
    a, b = uuid.uuid7(), uuid.uuid7()

    group_id = dao.create([a, b])

    assert group_id.version == 7
    rows = _members(project_db)
    assert len(rows) == 2
    assert {r.parallel_block_group_id for r in rows} == {group_id}
    assert {r.original_block_id for r in rows} == {a, b}


@pytest.mark.parametrize(
    "make_ids",
    [
        pytest.param(lambda a, b: [a, b, a], id="a-b-a"),
        pytest.param(lambda a, b: [b, a, b, a], id="b-a-b-a"),
    ],
)
def test_create_dedups_repeated_ids(project_db, make_ids) -> None:
    """Repeated block ids collapse via ``dict.fromkeys``; only distinct rows land."""
    dao = ParallelBlockGroupDAO(project_db)
    a, b = uuid.uuid7(), uuid.uuid7()

    group_id = dao.create(make_ids(a, b))

    rows = _members(project_db)
    assert len(rows) == 2
    assert _blocks_for_group(project_db, group_id) == {a, b}


@pytest.mark.parametrize(
    "make_arg",
    [
        pytest.param(lambda a: [], id="empty-list"),
        pytest.param(lambda a: [a], id="single"),
        pytest.param(lambda a: [a, a], id="single-duplicated"),
        pytest.param(lambda a: iter([a]), id="single-iterator"),
    ],
)
def test_create_fewer_than_two_distinct_raises_no_partial_write(
    project_db,
    make_arg,
) -> None:
    """Fewer than two distinct blocks raises ValueError and writes nothing."""
    dao = ParallelBlockGroupDAO(project_db)
    a = uuid.uuid7()

    with pytest.raises(
        ValueError,
        match="A parallel block group must contain at least two blocks",
    ):
        dao.create(make_arg(a))

    assert _members(project_db) == []


def test_create_preserves_first_seen_order(project_db) -> None:
    """``dict.fromkeys`` dedup keeps first-seen order; rows insert in that order.

    Passing ``[b, a, b]`` must stage exactly ``[b, a]`` (rowid/insertion order),
    not the sorted or set-arbitrary order -- proving the documented ordering
    contract, which the set-based dedup tests cannot observe.
    """
    dao = ParallelBlockGroupDAO(project_db)
    a, b = uuid.uuid7(), uuid.uuid7()

    dao.create([b, a, b])

    ordered = [row.original_block_id for row in _members(project_db)]
    assert ordered == [b, a]


def test_create_accepts_one_shot_generator(project_db) -> None:
    """A one-shot generator is materialized once; two rows are staged."""
    dao = ParallelBlockGroupDAO(project_db)
    a, b = uuid.uuid7(), uuid.uuid7()

    group_id = dao.create(iter([a, b]))

    assert group_id.version == 7
    assert _blocks_for_group(project_db, group_id) == {a, b}
    assert len(_members(project_db)) == 2


def test_create_member_already_in_confirmed_group_raises_before_insert(
    project_db,
) -> None:
    """If any block is already grouped, create raises and inserts nothing new."""
    dao = ParallelBlockGroupDAO(project_db)
    g0 = uuid.uuid7()
    a, b = uuid.uuid7(), uuid.uuid7()
    make_group_member(project_db, group_id=g0, original_block_id=a)  # committed

    with pytest.raises(
        ValueError,
        match="Blocks already belong to a confirmed group:",
    ) as excinfo:
        dao.create([a, b])

    assert str(a) in str(excinfo.value)
    # Only the pre-seeded row exists; b was never inserted.
    rows = _members(project_db)
    assert len(rows) == 1
    assert rows[0].original_block_id == a
    assert b not in _block_ids(project_db)


def test_create_already_grouped_message_lists_ids_sorted_as_strings(
    project_db,
) -> None:
    """The error message contains the offending ids sorted by their string form."""
    dao = ParallelBlockGroupDAO(project_db)
    g0 = uuid.uuid7()
    # Pick two committed ids where str(y) < str(x) to prove sorting is by string.
    id1, id2 = uuid.uuid7(), uuid.uuid7()
    x, y = (id1, id2) if str(id2) < str(id1) else (id2, id1)
    assert str(y) < str(x)
    z = uuid.uuid7()

    make_group_member(project_db, group_id=g0, original_block_id=x)
    make_group_member(project_db, group_id=g0, original_block_id=y)

    with pytest.raises(ValueError) as excinfo:
        dao.create([x, y, z])

    expected = f"Blocks already belong to a confirmed group: {sorted([str(x), str(y)])}"
    assert str(excinfo.value) == expected
    # No new group rows for z (only the two pre-seeded rows remain).
    assert _block_ids(project_db) == {x, y}


def test_create_block_grouped_and_duplicated_in_same_set_rejected(project_db) -> None:
    """A block already grouped, submitted twice in the same set, is still rejected."""
    dao = ParallelBlockGroupDAO(project_db)
    g0 = uuid.uuid7()
    a, b = uuid.uuid7(), uuid.uuid7()
    make_group_member(project_db, group_id=g0, original_block_id=a)

    with pytest.raises(
        ValueError,
        match="Blocks already belong to a confirmed group:",
    ):
        dao.create([a, a, b])

    # Only the pre-seeded row remains; b never inserted.
    rows = _members(project_db)
    assert len(rows) == 1
    assert rows[0].original_block_id == a
    assert b not in _block_ids(project_db)


def test_create_two_valid_creates_mint_distinct_monotonic_uuid7(project_db) -> None:
    """Two successive creates mint distinct, monotonically increasing uuid7 groups."""
    dao = ParallelBlockGroupDAO(project_db)
    a, b, c, d = (uuid.uuid7() for _ in range(4))

    g1 = dao.create([a, b])
    g2 = dao.create([c, d])

    assert g1.version == 7
    assert g2.version == 7
    assert g2 != g1
    assert g2 > g1  # uuid7 is monotonic within one process
    assert len(_members(project_db)) == 4
    assert _blocks_for_group(project_db, g1) == {a, b}
    assert _blocks_for_group(project_db, g2) == {c, d}


def test_create_does_not_commit_rolled_back(project_db) -> None:
    """create only stages; a rollback discards the staged rows entirely."""
    dao = ParallelBlockGroupDAO(project_db)
    a, b = uuid.uuid7(), uuid.uuid7()

    dao.create([a, b])
    assert len(_members(project_db)) == 2  # visible via autoflush pre-commit

    project_db.rollback()

    assert _members(project_db) == []


def test_create_persists_across_fresh_session_once_committed(
    project_db,
    project,
) -> None:
    """After an explicit commit, a brand-new session sees the created rows."""
    dao = ParallelBlockGroupDAO(project_db)
    a, b = uuid.uuid7(), uuid.uuid7()

    group_id = dao.create([a, b])
    project_db.commit()

    other = get_session(general_db(project.pk))
    try:
        rows = list(other.scalars(select(ParallelBlockGroupMember)).all())
        assert len(rows) == 2
        assert {r.parallel_block_group_id for r in rows} == {group_id}
        assert {r.original_block_id for r in rows} == {a, b}
    finally:
        other.close()


# ---------------------------------------------------------------------------
# -- get_all_groups
# ---------------------------------------------------------------------------


def test_get_all_groups_empty_returns_real_empty_dict(project_db) -> None:
    """An empty table yields a genuine (materialized) empty dict, not a defaultdict."""
    dao = ParallelBlockGroupDAO(project_db)

    result = dao.get_all_groups()

    assert type(result) is dict
    assert result == {}


def test_get_all_groups_single_group_two_element_list(project_db) -> None:
    """A single group with two members returns one key mapping to both blocks."""
    dao = ParallelBlockGroupDAO(project_db)
    g1 = uuid.uuid7()
    a, b = uuid.uuid7(), uuid.uuid7()
    make_group_member(project_db, group_id=g1, original_block_id=a)
    make_group_member(project_db, group_id=g1, original_block_id=b)

    result = dao.get_all_groups()

    assert set(result) == {g1}
    assert len(result[g1]) == 2
    assert set(result[g1]) == {a, b}


def test_get_all_groups_multiple_groups_partitioned_by_id(project_db) -> None:
    """Interleaved members are partitioned into the correct groups by group id."""
    dao = ParallelBlockGroupDAO(project_db)
    g1, g2 = uuid.uuid7(), uuid.uuid7()
    a, b = uuid.uuid7(), uuid.uuid7()
    c, d, e = uuid.uuid7(), uuid.uuid7(), uuid.uuid7()
    # Interleave insert order to prove partitioning is by id, not order.
    make_group_member(project_db, group_id=g1, original_block_id=a)
    make_group_member(project_db, group_id=g2, original_block_id=c)
    make_group_member(project_db, group_id=g1, original_block_id=b)
    make_group_member(project_db, group_id=g2, original_block_id=d)
    make_group_member(project_db, group_id=g2, original_block_id=e)

    result = dao.get_all_groups()

    assert set(result) == {g1, g2}
    assert set(result[g1]) == {a, b}
    assert set(result[g2]) == {c, d, e}


@pytest.mark.parametrize("count", [1, 2, 3, 6])
def test_get_all_groups_no_size_filter(project_db, count) -> None:
    """Groups of any size are returned verbatim; singletons are not filtered out."""
    dao = ParallelBlockGroupDAO(project_db)
    g1 = uuid.uuid7()
    blocks = {uuid.uuid7() for _ in range(count)}
    for block in blocks:
        make_group_member(project_db, group_id=g1, original_block_id=block)

    result = dao.get_all_groups()

    assert set(result) == {g1}
    assert len(result[g1]) == count
    assert set(result[g1]) == blocks


def test_get_all_groups_reads_staged_uncommitted_inserts(project_db) -> None:
    """get_all_groups sees rows staged by create in the same session (autoflush)."""
    dao = ParallelBlockGroupDAO(project_db)
    a, b, c, d = (uuid.uuid7() for _ in range(4))

    g = dao.create([a, b])
    g2 = dao.create([c, d])

    result = dao.get_all_groups()

    assert set(result) == {g, g2}
    assert set(result[g]) == {a, b}
    assert set(result[g2]) == {c, d}


# ---------------------------------------------------------------------------
# -- clear_all
# ---------------------------------------------------------------------------


def test_clear_all_empty_returns_zero(project_db) -> None:
    """Clearing an empty table deletes nothing and leaves it empty."""
    dao = ParallelBlockGroupDAO(project_db)

    deleted = dao.clear_all()

    assert deleted == 0
    assert dao.get_all_groups() == {}


def test_clear_all_returns_member_rowcount_and_empties(project_db) -> None:
    """clear_all reports the number of member rows deleted, not the group count."""
    dao = ParallelBlockGroupDAO(project_db)
    g1, g2 = uuid.uuid7(), uuid.uuid7()
    a, b, c, d, e = (uuid.uuid7() for _ in range(5))
    make_group_member(project_db, group_id=g1, original_block_id=a)
    make_group_member(project_db, group_id=g1, original_block_id=b)
    make_group_member(project_db, group_id=g2, original_block_id=c)
    make_group_member(project_db, group_id=g2, original_block_id=d)
    make_group_member(project_db, group_id=g2, original_block_id=e)

    deleted = dao.clear_all()

    assert deleted == 5
    assert dao.get_all_groups() == {}


def test_clear_all_rollback_restores_commit_is_durable(project_db, project) -> None:
    """clear_all only stages a DELETE: rollback restores rows; commit makes it durable."""
    dao = ParallelBlockGroupDAO(project_db)
    g1 = uuid.uuid7()
    a, b = uuid.uuid7(), uuid.uuid7()
    make_group_member(project_db, group_id=g1, original_block_id=a)
    make_group_member(project_db, group_id=g1, original_block_id=b)  # committed

    # Staged delete, then discarded -> the two committed rows come back.
    deleted = dao.clear_all()
    assert deleted == 2
    project_db.rollback()
    assert len(_members(project_db)) == 2
    assert _block_ids(project_db) == {a, b}

    # Now clear for real and commit; a fresh session observes zero rows.
    assert dao.clear_all() == 2
    project_db.commit()

    other = get_session(general_db(project.pk))
    try:
        assert other.scalars(select(ParallelBlockGroupMember)).all() == []
    finally:
        other.close()


def test_clear_all_then_create_same_session_clears_before_insert(project_db) -> None:
    """clear_all followed by create in one session yields only the new group."""
    dao = ParallelBlockGroupDAO(project_db)
    g_old = uuid.uuid7()
    a, b = uuid.uuid7(), uuid.uuid7()
    make_group_member(project_db, group_id=g_old, original_block_id=a)
    make_group_member(project_db, group_id=g_old, original_block_id=b)

    assert dao.clear_all() == 2
    c, d = uuid.uuid7(), uuid.uuid7()
    g_new = dao.create([c, d])

    result = dao.get_all_groups()
    assert set(result) == {g_new}
    assert set(result[g_new]) == {c, d}


def test_clear_all_then_recreate_reusing_cleared_block_succeeds(project_db) -> None:
    """A block freed by clear_all can be re-used in a new group (autoflush ordering)."""
    dao = ParallelBlockGroupDAO(project_db)
    g_old = uuid.uuid7()
    a, b = uuid.uuid7(), uuid.uuid7()
    make_group_member(project_db, group_id=g_old, original_block_id=a)
    make_group_member(project_db, group_id=g_old, original_block_id=b)

    dao.clear_all()
    c = uuid.uuid7()
    g_new = dao.create([a, c])  # reuse a, previously grouped

    result = dao.get_all_groups()
    assert set(result) == {g_new}
    assert set(result[g_new]) == {a, c}


# ---------------------------------------------------------------------------
# -- full lifecycle
# ---------------------------------------------------------------------------


def test_full_lifecycle_create_get_clear_get(project_db) -> None:
    """create -> get_all_groups -> clear_all -> get_all_groups round trip."""
    dao = ParallelBlockGroupDAO(project_db)
    a, b = uuid.uuid7(), uuid.uuid7()

    g = dao.create([a, b])

    after_create = dao.get_all_groups()
    assert set(after_create) == {g}
    assert set(after_create[g]) == {a, b}
    assert len(after_create[g]) == 2

    assert dao.clear_all() == 2
    assert dao.get_all_groups() == {}


# ---------------------------------------------------------------------------
# -- ParallelBlockGroupMember constraints
# ---------------------------------------------------------------------------


def test_unique_original_block_id_across_groups_raises(project_db) -> None:
    """The UNIQUE(original_block_id) constraint blocks a block joining two groups."""
    g1, g2 = uuid.uuid7(), uuid.uuid7()
    a = uuid.uuid7()
    make_group_member(project_db, group_id=g1, original_block_id=a)  # committed

    with pytest.raises(IntegrityError):
        # Same block, different group id -> violates UNIQUE on original_block_id.
        # make_group_member flushes internally, which is what raises here.
        make_group_member(project_db, group_id=g2, original_block_id=a, commit=False)

    project_db.rollback()

    rows = _members(project_db)
    assert len(rows) == 1
    assert rows[0].parallel_block_group_id == g1
    assert rows[0].original_block_id == a


def test_composite_pk_two_blocks_same_group_allowed(project_db) -> None:
    """Two distinct blocks under one group id both persist (composite PK)."""
    g1 = uuid.uuid7()
    a, b = uuid.uuid7(), uuid.uuid7()

    make_group_member(project_db, group_id=g1, original_block_id=a)
    make_group_member(project_db, group_id=g1, original_block_id=b)

    rows = _members(project_db)
    assert len(rows) == 2
    assert {r.parallel_block_group_id for r in rows} == {g1}
    assert {r.original_block_id for r in rows} == {a, b}


def test_exact_duplicate_row_raises_integrity_error(project_db) -> None:
    """Inserting an identical (group, block) row again violates the PK/UNIQUE."""
    g1 = uuid.uuid7()
    a = uuid.uuid7()
    make_group_member(project_db, group_id=g1, original_block_id=a)  # committed

    with pytest.raises(IntegrityError):
        # make_group_member flushes internally, which is what raises here.
        make_group_member(project_db, group_id=g1, original_block_id=a, commit=False)

    project_db.rollback()

    rows = _members(project_db)
    assert len(rows) == 1
    assert rows[0].parallel_block_group_id == g1
    assert rows[0].original_block_id == a
