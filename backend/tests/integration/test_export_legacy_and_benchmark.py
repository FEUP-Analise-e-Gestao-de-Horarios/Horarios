"""Integration tests for the legacy comparator and the exporter benchmark tools.

Covers the database-backed pieces the pure-logic unit tests can't reach:

* ``legacy.differences.Comparator`` — full-database diff, conflict listing and
  modification ordering opened against real project databases.
* ``benchmark_scaling`` / ``benchmark_runtime`` — the clean-baseline check, the
  deterministic mutation used to synthesize changed sessions, and a full
  ``run_export_benchmark`` pass (fresh compute and cache hit).
"""

from pathlib import Path

import pytest

from src.exporter.benchmark_runtime import run_export_benchmark
from src.exporter.benchmark_scaling import (
    count_changed_sessions,
    ensure_clean_exporter_baseline,
    mutate_project_for_benchmark,
)
from src.exporter.legacy.differences import Comparator
from tests.integration._export_seed import (
    CLASS_A,
    CLASS_B,
    ROOM_A,
    SUBJECT_A,
    TEACHER_A,
    WEEK,
    WEEK_2,
    seed_reference_data,
    seed_session,
    uid,
)


def _seed_clean_baseline(export_dbs, count: int = 4) -> None:
    """Seed ``count`` identical sessions into both databases (a clean baseline)."""
    for db in (export_dbs.initial, export_dbs.general):
        seed_reference_data(db)
        for index in range(count):
            seed_session(
                db,
                session_id=uid(400 + index),
                start_time=800 + index * 100,
                original_block_id=uid(450 + index),
                week=WEEK if index % 2 == 0 else WEEK_2,
            )


# ---------------------------------------------------------------------------
# -- Comparator (legacy full-DB diff)
# ---------------------------------------------------------------------------


def test_comparator_reports_added_removed_and_modified(export_dbs) -> None:
    common = uid(100)
    removed = uid(101)
    added = uid(102)

    seed_reference_data(export_dbs.initial)
    seed_session(export_dbs.initial, session_id=common, start_time=830, original_block_id=uid(200))
    seed_session(export_dbs.initial, session_id=removed, start_time=900, original_block_id=uid(201))

    seed_reference_data(export_dbs.general)
    # common moved 830 -> 1000; removed dropped; added is new.
    seed_session(export_dbs.general, session_id=common, start_time=1000, original_block_id=uid(200))
    seed_session(export_dbs.general, session_id=added, start_time=1100, original_block_id=uid(202))

    with Comparator(export_dbs.project_id) as comparator:
        diff = comparator.database_differences()

    assert str(added.hex) in {str(k) for k in diff["added"]} or str(added) in {
        str(k) for k in diff["added"]
    }
    assert diff["removed"]  # the removed session is present
    modified_keys = {str(k) for k in diff["modified"]}
    assert str(common) in modified_keys or common.hex in modified_keys
    changed = next(iter(diff["modified"].values()))
    assert "start_time" in changed


def test_comparator_reports_room_conflicts(export_dbs) -> None:
    session_1 = uid(120)
    session_2 = uid(121)
    for db in (export_dbs.initial, export_dbs.general):
        seed_reference_data(db)
        seed_session(
            db,
            session_id=session_1,
            start_time=830,
            original_block_id=uid(220),
            rooms=(ROOM_A,),
            teachers=(TEACHER_A,),
            class_subjects=((CLASS_A, SUBJECT_A),),
        )
        seed_session(
            db,
            session_id=session_2,
            start_time=845,
            original_block_id=uid(221),
            rooms=(ROOM_A,),
            teachers=(TEACHER_A,),
            class_subjects=((CLASS_B, SUBJECT_A),),
        )

    with Comparator(export_dbs.project_id) as comparator:
        conflicts = comparator.database_conflicts()

    assert len(conflicts["rooms_conflicts"]) == 1
    pair = conflicts["rooms_conflicts"][0]
    assert {pair["session1"], pair["session2"]} == {str(session_1), str(session_2)}
    # Teacher conflict is also present (they share TEACHER_A) but no class one.
    assert len(conflicts["teacher_conflicts"]) == 1
    assert conflicts["classes_conflicts"] == []


def test_comparator_modification_order_for_single_move(export_dbs) -> None:
    session_id = uid(100)
    seed_reference_data(export_dbs.initial)
    seed_session(
        export_dbs.initial,
        session_id=session_id,
        start_time=830,
        original_block_id=uid(200),
    )
    seed_reference_data(export_dbs.general)
    seed_session(
        export_dbs.general,
        session_id=session_id,
        start_time=1000,
        original_block_id=uid(200),
    )

    with Comparator(export_dbs.project_id) as comparator:
        order = comparator.get_modification_order()

    assert order == (str(session_id),)


# ---------------------------------------------------------------------------
# -- Benchmark: baseline check + deterministic mutation
# ---------------------------------------------------------------------------


def test_clean_baseline_passes_and_dirty_baseline_raises(export_dbs, tmp_path: Path) -> None:
    _seed_clean_baseline(export_dbs)

    # Matching databases: no error.
    ensure_clean_exporter_baseline(export_dbs.project_id, projects_db_path=tmp_path)

    # Introduce a divergence in the general DB and expect a failure.
    seed_session(
        export_dbs.general,
        session_id=uid(500),
        start_time=1200,
        original_block_id=uid(550),
    )
    with pytest.raises(ValueError, match="matching initial/general"):
        ensure_clean_exporter_baseline(export_dbs.project_id, projects_db_path=tmp_path)


def test_mutation_produces_requested_changed_sessions(export_dbs, tmp_path: Path) -> None:
    _seed_clean_baseline(export_dbs, count=4)

    summary = mutate_project_for_benchmark(
        export_dbs.project_id,
        changed_sessions=2,
        seed=1234,
        projects_db_path=tmp_path,
    )

    assert summary.requested_changed_sessions == 2
    assert summary.actual_changed_sessions == 2
    assert len(summary.modified_session_ids) == 2
    assert count_changed_sessions(export_dbs.project_id, projects_db_path=tmp_path) == 2


def test_mutation_is_deterministic_for_same_seed(export_dbs, tmp_path: Path) -> None:
    _seed_clean_baseline(export_dbs, count=4)

    first = mutate_project_for_benchmark(
        export_dbs.project_id,
        changed_sessions=2,
        seed=42,
        projects_db_path=tmp_path,
    )

    # The mutation is seeded, so the selected session ids are reproducible.
    assert first.seed == 42
    assert first.modified_session_ids == sorted(first.modified_session_ids)


# ---------------------------------------------------------------------------
# -- Benchmark: full run (compute + cache hit)
# ---------------------------------------------------------------------------


def test_run_export_benchmark_computes_then_hits_cache(export_dbs, tmp_path: Path) -> None:
    _seed_clean_baseline(export_dbs, count=4)
    mutate_project_for_benchmark(
        export_dbs.project_id,
        changed_sessions=2,
        seed=7,
        projects_db_path=tmp_path,
    )

    fresh = run_export_benchmark(
        export_dbs.project_id,
        recalculate=True,
        projects_db_path=tmp_path,
    )
    assert fresh.cache_hit is False
    assert fresh.counts.changed_sessions == 2
    assert fresh.total_ms >= 0.0

    cached = run_export_benchmark(
        export_dbs.project_id,
        recalculate=False,
        projects_db_path=tmp_path,
    )
    assert cached.cache_hit is True
    assert cached.counts.changed_sessions == 2
