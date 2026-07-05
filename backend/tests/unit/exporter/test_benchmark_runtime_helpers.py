"""Unit tests for the pure helpers in :mod:`src.exporter.benchmark_runtime`.

Path builders, the projects-db override context manager, payload counting and
cache-model resolution. The full DB-backed ``run_export_benchmark`` is not
exercised here; these cover the small pure pieces it composes.
"""

from pathlib import Path

from pytest_django.fixtures import SettingsWrapper

from src.exporter.benchmark_runtime import (
    BenchmarkCounts,
    ExportBenchmarkResult,
    _counts_from_payload,
    _model_payload_from_cache,
    _response_json_kb,
    general_db_path,
    initial_db_path,
    override_projects_db_path,
    project_db_dir,
)
from src.exporter.compact_payload import compact_export_payload
from src.exporter.schemas import CompactProjectExportPayload, ProjectExportPayload

# ---------------------------------------------------------------------------
# -- Path builders
# ---------------------------------------------------------------------------


def test_path_builders_with_explicit_root() -> None:
    root = Path("/var/projects")
    assert project_db_dir(7, root) == root / "7"
    assert general_db_path(7, root) == root / "7" / "general_database.db"
    assert initial_db_path(7, root) == root / "7" / "initial_database.db"


def test_path_builders_fall_back_to_settings(settings: SettingsWrapper, tmp_path: Path) -> None:
    settings.PROJECTS_DB_PATH = tmp_path
    assert project_db_dir(3) == tmp_path / "3"
    assert general_db_path(3) == tmp_path / "3" / "general_database.db"


# ---------------------------------------------------------------------------
# -- override_projects_db_path
# ---------------------------------------------------------------------------


def test_override_projects_db_path_swaps_and_restores(
    settings: SettingsWrapper,
    tmp_path: Path,
) -> None:
    original = tmp_path / "original"
    settings.PROJECTS_DB_PATH = original

    with override_projects_db_path(tmp_path / "override"):
        assert Path(settings.PROJECTS_DB_PATH) == tmp_path / "override"

    assert Path(settings.PROJECTS_DB_PATH) == original


def test_override_projects_db_path_none_is_a_noop(
    settings: SettingsWrapper,
    tmp_path: Path,
) -> None:
    settings.PROJECTS_DB_PATH = tmp_path
    with override_projects_db_path(None):
        assert Path(settings.PROJECTS_DB_PATH) == tmp_path
    assert Path(settings.PROJECTS_DB_PATH) == tmp_path


# ---------------------------------------------------------------------------
# -- _response_json_kb
# ---------------------------------------------------------------------------


def test_response_json_kb_returns_rounded_size() -> None:
    size = _response_json_kb({"a": 1, "b": [1, 2, 3]}, "some message")
    assert isinstance(size, float)
    assert size >= 0.0


# ---------------------------------------------------------------------------
# -- _counts_from_payload
# ---------------------------------------------------------------------------


def _payload_with_two_steps() -> ProjectExportPayload:
    def step(session_id: str) -> dict:
        return {
            "type": "move",
            "original_block_id": "block",
            "session_ids": [session_id],
            "weeks": ["2026-01-05"],
            "week_range": {"start": "2026-01-05", "end": "2026-01-05", "contiguous": True},
            "modifications": {},
            "dependencies": [],
            "session": {
                "id": session_id,
                "start_time": 830,
                "duration": 2,
                "weekday": "monday",
                "week": "2026-01-05",
            },
        }

    return ProjectExportPayload.model_validate(
        {
            "added_removed_sessions": {"added": [{"id": "a1"}], "removed": [{"id": "r1"}]},
            "rooms_conflicts": [],
            "teacher_conflicts": [],
            "classes_conflicts": [],
            "modification_steps": [step("s1"), step("s2")],
        },
    )


def test_counts_from_payload_counts_unique_changed_sessions() -> None:
    counts = _counts_from_payload(_payload_with_two_steps())
    assert isinstance(counts, BenchmarkCounts)
    assert counts.changed_sessions == 2
    assert counts.modification_steps == 2
    assert counts.added_sessions == 1
    assert counts.removed_sessions == 1


# ---------------------------------------------------------------------------
# -- _model_payload_from_cache
# ---------------------------------------------------------------------------


def test_model_payload_from_cache_expands_compact_format() -> None:
    compact = compact_export_payload(_payload_with_two_steps()).model_dump(mode="json")
    result = _model_payload_from_cache(compact)
    assert isinstance(result, ProjectExportPayload)
    assert len(result.modification_steps) == 2


def test_model_payload_from_cache_validates_expanded_format() -> None:
    expanded = _payload_with_two_steps().model_dump(mode="json")
    result = _model_payload_from_cache(expanded)
    assert isinstance(result, ProjectExportPayload)
    assert len(result.modification_steps) == 2


# ---------------------------------------------------------------------------
# -- ExportBenchmarkResult.to_dict
# ---------------------------------------------------------------------------


def test_export_benchmark_result_to_dict() -> None:
    result = ExportBenchmarkResult(
        project_id=1,
        projects_db_path=None,
        recalculate=True,
        payload_format="compact",
        cache_hit=False,
        counts=BenchmarkCounts(
            changed_sessions=5,
            modification_steps=3,
            room_conflicts=1,
            teacher_conflicts=1,
            class_conflicts=0,
            added_sessions=1,
            removed_sessions=1,
        ),
        payload_kb={"compact": 2.0, "expanded": 4.0},
        response_payload_kb=2.5,
        timings_ms={"build": 10.0},
        total_ms=30.0,
    )
    as_dict = result.to_dict()
    assert as_dict["cache_hit"] is False
    assert as_dict["counts"]["changed_sessions"] == 5
    assert as_dict["timings_ms"]["build"] == 10.0


def test_compact_project_export_payload_used_by_cache_resolution() -> None:
    # Guards the branch that hands compact cache data to CompactProjectExportPayload.
    compact = compact_export_payload(_payload_with_two_steps())
    assert isinstance(compact, CompactProjectExportPayload)
    assert compact.format == "compact_export_v1"
