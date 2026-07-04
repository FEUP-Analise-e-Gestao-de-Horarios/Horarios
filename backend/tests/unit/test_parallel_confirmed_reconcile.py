"""Unit tests for ``ParallelBlockCandidateDAO.reconcile_confirmed_subjects``.

Reconciliation is the heart of the confirmation feature: a subject counts as
confirmed only when *every* one of its current candidate components is stored,
and the stored set is pruned to exactly the ids of fully-confirmed subjects on
every read. Components are constructed directly here (no slot seeding needed)
since reconciliation only reads each component's ``candidate_group_id`` and
``subject_id``.
"""

import random
import uuid

import pytest

from src.projects.projects_db.dao.parallel_block_candidate_dao import ParallelBlockCandidateDAO
from src.projects.projects_db.dao.parallel_candidate_graph import CandidateComponent
from src.projects.projects_db.dao.parallel_confirmed_candidate_dao import (
    ParallelConfirmedCandidateDAO,
)
from tests.factories import make_confirmed_candidate


def _component(subject_id: uuid.UUID, candidate_group_id: uuid.UUID) -> CandidateComponent:
    return CandidateComponent(
        candidate_group_id=candidate_group_id,
        subject_id=subject_id,
        block_ids=frozenset(),
        edges=(),
    )


def test_no_stored_confirmations_returns_empty(project_db) -> None:
    """With nothing stored, no subject is confirmed and nothing is written."""
    dao = ParallelBlockCandidateDAO(project_db)
    subject = uuid.uuid7()
    components = [_component(subject, uuid.uuid7())]

    assert dao.reconcile_confirmed_subjects(components) == set()
    assert ParallelConfirmedCandidateDAO(project_db).get_all() == set()


def test_fully_confirmed_subject_is_reported_and_kept(project_db) -> None:
    """A subject with all its candidates stored is confirmed; ids survive."""
    subject = uuid.uuid7()
    c1, c2 = uuid.uuid7(), uuid.uuid7()
    make_confirmed_candidate(project_db, candidate_group_id=c1, commit=False)
    make_confirmed_candidate(project_db, candidate_group_id=c2, commit=False)

    dao = ParallelBlockCandidateDAO(project_db)
    result = dao.reconcile_confirmed_subjects([_component(subject, c1), _component(subject, c2)])

    assert result == {subject}
    assert ParallelConfirmedCandidateDAO(project_db).get_all() == {c1, c2}


def test_partial_subject_is_not_confirmed_and_pruned(project_db) -> None:
    """A subject with only some candidates stored is unconfirmed; its id is pruned."""
    subject = uuid.uuid7()
    c1, c2 = uuid.uuid7(), uuid.uuid7()
    # Only one of the subject's two current candidates is stored.
    make_confirmed_candidate(project_db, candidate_group_id=c1, commit=False)

    dao = ParallelBlockCandidateDAO(project_db)
    result = dao.reconcile_confirmed_subjects([_component(subject, c1), _component(subject, c2)])

    assert result == set()
    assert ParallelConfirmedCandidateDAO(project_db).get_all() == set()


def test_orphan_stored_id_is_pruned(project_db) -> None:
    """A stored id matching no current component is deleted."""
    subject = uuid.uuid7()
    live = uuid.uuid7()
    orphan = uuid.uuid7()
    make_confirmed_candidate(project_db, candidate_group_id=live, commit=False)
    make_confirmed_candidate(project_db, candidate_group_id=orphan, commit=False)

    dao = ParallelBlockCandidateDAO(project_db)
    result = dao.reconcile_confirmed_subjects([_component(subject, live)])

    assert result == {subject}
    assert ParallelConfirmedCandidateDAO(project_db).get_all() == {live}


def test_no_components_prunes_all_stored(project_db) -> None:
    """When candidates disappear entirely, every stored id is an orphan."""
    make_confirmed_candidate(project_db, candidate_group_id=uuid.uuid7(), commit=False)
    make_confirmed_candidate(project_db, candidate_group_id=uuid.uuid7(), commit=False)

    dao = ParallelBlockCandidateDAO(project_db)

    assert dao.reconcile_confirmed_subjects([]) == set()
    assert ParallelConfirmedCandidateDAO(project_db).get_all() == set()


def test_mixed_subjects_only_full_ones_survive(project_db) -> None:
    """One fully-confirmed subject is kept while a partial neighbour is pruned."""
    full = uuid.uuid7()
    partial = uuid.uuid7()
    f1, f2 = uuid.uuid7(), uuid.uuid7()
    p1, p2 = uuid.uuid7(), uuid.uuid7()
    for cid in (f1, f2, p1):  # partial: only p1 stored, p2 missing
        make_confirmed_candidate(project_db, candidate_group_id=cid, commit=False)

    dao = ParallelBlockCandidateDAO(project_db)
    result = dao.reconcile_confirmed_subjects(
        [
            _component(full, f1),
            _component(full, f2),
            _component(partial, p1),
            _component(partial, p2),
        ],
    )

    assert result == {full}
    assert ParallelConfirmedCandidateDAO(project_db).get_all() == {f1, f2}


def test_two_fully_confirmed_subjects_both_survive_union_kept(project_db) -> None:
    """Two independently-full subjects are both reported; kept ids are their union."""
    subject_x, subject_y = uuid.uuid7(), uuid.uuid7()
    x1, x2 = uuid.uuid7(), uuid.uuid7()
    y1, y2 = uuid.uuid7(), uuid.uuid7()
    for cid in (x1, x2, y1, y2):
        make_confirmed_candidate(project_db, candidate_group_id=cid, commit=False)

    dao = ParallelBlockCandidateDAO(project_db)
    result = dao.reconcile_confirmed_subjects(
        [
            _component(subject_x, x1),
            _component(subject_x, x2),
            _component(subject_y, y1),
            _component(subject_y, y2),
        ],
    )

    # Neither full subject is dropped and no kept id is over-pruned.
    assert result == {subject_x, subject_y}
    assert ParallelConfirmedCandidateDAO(project_db).get_all() == {x1, x2, y1, y2}


def test_stored_matches_all_candidates_is_noop(project_db) -> None:
    """When the stored set already equals every candidate, reconcile deletes nothing."""
    subject = uuid.uuid7()
    c1, c2 = uuid.uuid7(), uuid.uuid7()
    make_confirmed_candidate(project_db, candidate_group_id=c1, commit=False)
    make_confirmed_candidate(project_db, candidate_group_id=c2, commit=False)

    dao = ParallelBlockCandidateDAO(project_db)
    result = dao.reconcile_confirmed_subjects([_component(subject, c1), _component(subject, c2)])

    assert result == {subject}
    # No valid row was deleted.
    assert ParallelConfirmedCandidateDAO(project_db).get_all() == {c1, c2}


def test_confirmed_subject_with_shrunk_candidate_set_prunes_gone_id(project_db) -> None:
    """A still-confirmed subject that lost a candidate keeps the live id, prunes the gone one.

    Distinct from the orphan case: ``c2`` still belongs to *this* subject in the
    stored set, but the subject no longer emits a component for it, so its live
    candidate set is ``{c1}`` -- fully confirmed -- and ``c2`` is pruned.
    """
    subject = uuid.uuid7()
    c1, c2 = uuid.uuid7(), uuid.uuid7()
    make_confirmed_candidate(project_db, candidate_group_id=c1, commit=False)
    make_confirmed_candidate(project_db, candidate_group_id=c2, commit=False)

    dao = ParallelBlockCandidateDAO(project_db)
    # Only c1 is a current candidate of the subject now.
    result = dao.reconcile_confirmed_subjects([_component(subject, c1)])

    assert result == {subject}
    assert ParallelConfirmedCandidateDAO(project_db).get_all() == {c1}


@pytest.mark.parametrize("n_subjects", [1, 3, 5, 10])
def test_reconcile_invariant_over_many_subjects(project_db, n_subjects: int) -> None:
    """Property-style check of the reconcile invariant over a generated input.

    Deterministically (fixed seed) builds ``n_subjects`` subjects, each with a
    random non-empty candidate id set, stores a random subset of all those ids
    plus a couple of orphan ids, then asserts the invariant *independently* of
    the DAO implementation:

    * the returned subject ids are exactly those whose full candidate set is a
      subset of the stored set;
    * the stored set after the call equals the union of those fully-confirmed
      subjects' candidate ids (stale and partial ids pruned, survivors kept).

    Orphan stored ids (belonging to no component) are always added, so pruning
    is exercised in every parametrization; the per-id coin flip additionally
    produces partial subjects for the larger cases.
    """
    rng = random.Random(1234 + n_subjects)

    # Build subjects, each with a fresh random candidate id set.
    candidates_by_subject: dict[uuid.UUID, set[uuid.UUID]] = {}
    for _ in range(n_subjects):
        subject_id = uuid.uuid4()
        n_candidates = rng.randint(1, 4)
        candidates_by_subject[subject_id] = {uuid.uuid4() for _ in range(n_candidates)}

    all_candidate_ids = {cid for cids in candidates_by_subject.values() for cid in cids}

    # Store a random subset of the real candidate ids...
    stored = {cid for cid in all_candidate_ids if rng.random() < 0.5}
    # ...plus orphan ids that belong to no component, to force pruning.
    orphans = {uuid.uuid4() for _ in range(2)}
    stored |= orphans

    for cid in stored:
        make_confirmed_candidate(project_db, candidate_group_id=cid, commit=False)

    components = [
        _component(subject_id, cid)
        for subject_id, cids in candidates_by_subject.items()
        for cid in cids
    ]

    # Independently-computed expectation.
    expected_confirmed = {
        subject_id for subject_id, cids in candidates_by_subject.items() if cids <= stored
    }
    expected_keep = {
        cid for subject_id in expected_confirmed for cid in candidates_by_subject[subject_id]
    }

    dao = ParallelBlockCandidateDAO(project_db)
    result = dao.reconcile_confirmed_subjects(components)

    assert result == expected_confirmed
    assert ParallelConfirmedCandidateDAO(project_db).get_all() == expected_keep
    # Pruning was genuinely exercised: the orphans never survive.
    assert orphans.isdisjoint(ParallelConfirmedCandidateDAO(project_db).get_all())
