"""DAO-level tests for :class:`ParallelConfirmedCandidateDAO`.

These run against a real, seeded per-project SQLAlchemy SQLite file (the
``project_db`` fixture yields a live ``Session``). The DAO stores an opaque set
of ``candidate_group_id`` values; there is no subject column, so every check
here is purely about set membership and pruning.

Like the other parallel DAOs, ``add`` / ``remove`` / ``retain_only`` /
``clear_all`` only *stage* work on the session -- the caller commits.
"""

import uuid

from src.projects.projects_db.dao.parallel_confirmed_candidate_dao import (
    ParallelConfirmedCandidateDAO,
)
from tests.factories import make_confirmed_candidate


def test_get_all_empty_returns_empty_set(project_db) -> None:
    """A pristine DB has no confirmations."""
    assert ParallelConfirmedCandidateDAO(project_db).get_all() == set()


def test_add_inserts_and_is_idempotent(project_db) -> None:
    """add stages new ids and silently ignores ones already stored."""
    dao = ParallelConfirmedCandidateDAO(project_db)
    a, b = uuid.uuid7(), uuid.uuid7()

    assert dao.add([a, b, a]) == [a, b]
    assert dao.get_all() == {a, b}

    # Re-adding a stored id plus a new one only inserts the new one.
    c = uuid.uuid7()
    dao.add([a, c])
    assert dao.get_all() == {a, b, c}


def test_add_empty_is_noop(project_db) -> None:
    dao = ParallelConfirmedCandidateDAO(project_db)
    assert dao.add([]) == []
    assert dao.get_all() == set()


def test_remove_deletes_only_named_ids(project_db) -> None:
    dao = ParallelConfirmedCandidateDAO(project_db)
    a, b, c = uuid.uuid7(), uuid.uuid7(), uuid.uuid7()
    dao.add([a, b, c])

    removed = dao.remove([a, c, uuid.uuid7()])

    assert removed == 2
    assert dao.get_all() == {b}


def test_retain_only_prunes_everything_outside_keep(project_db) -> None:
    dao = ParallelConfirmedCandidateDAO(project_db)
    a, b, c = uuid.uuid7(), uuid.uuid7(), uuid.uuid7()
    dao.add([a, b, c])

    removed = dao.retain_only({a})

    assert removed == 2
    assert dao.get_all() == {a}


def test_retain_only_empty_keep_clears_all(project_db) -> None:
    dao = ParallelConfirmedCandidateDAO(project_db)
    dao.add([uuid.uuid7(), uuid.uuid7()])

    removed = dao.retain_only(set())

    assert removed == 2
    assert dao.get_all() == set()


def test_clear_all_removes_every_row(project_db) -> None:
    dao = ParallelConfirmedCandidateDAO(project_db)
    dao.add([uuid.uuid7(), uuid.uuid7()])

    assert dao.clear_all() == 2
    assert dao.get_all() == set()


def test_seeded_rows_visible_through_dao(project_db) -> None:
    """Rows seeded via the factory are read back by the DAO."""
    a, b = uuid.uuid7(), uuid.uuid7()
    make_confirmed_candidate(project_db, candidate_group_id=a)
    make_confirmed_candidate(project_db, candidate_group_id=b)

    assert ParallelConfirmedCandidateDAO(project_db).get_all() == {a, b}
