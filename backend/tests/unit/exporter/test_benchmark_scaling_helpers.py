"""Unit tests for the pure helpers in :mod:`src.exporter.benchmark_scaling`.

Statistics and artifact-serialization helpers used by the exporter scaling
benchmark. No database is touched here (the DB-backed mutation helpers are
covered by the in-repo ``src/exporter/tests.py``); these pin the maths and the
JSON/CSV artifact shape.
"""

import json
from pathlib import Path

from pytest import approx, mark

from src.exporter.benchmark_runtime import BenchmarkCounts, ExportBenchmarkResult
from src.exporter.benchmark_scaling import (
    MutationSummary,
    ScalingRunRecord,
    _minutes_to_hhmm,
    _shift_start_time,
    build_scaling_artifact,
    build_size_summary,
    dominant_phase,
    doubling_ratios,
    linear_fit_estimate,
    median_phase_timings,
    percentile_nearest_rank,
    write_scaling_artifacts,
)


def make_benchmark(*, total_ms: float, timings: dict[str, float]) -> ExportBenchmarkResult:
    return ExportBenchmarkResult(
        project_id=1,
        projects_db_path=None,
        recalculate=True,
        payload_format="compact",
        cache_hit=False,
        counts=BenchmarkCounts(
            changed_sessions=5,
            modification_steps=3,
            room_conflicts=1,
            teacher_conflicts=0,
            class_conflicts=0,
            added_sessions=1,
            removed_sessions=1,
        ),
        payload_kb={"compact": 2.0, "expanded": 4.0},
        response_payload_kb=2.5,
        timings_ms=timings,
        total_ms=total_ms,
    )


def make_record(
    *,
    size: int,
    run_number: int,
    total_ms: float,
    timings: dict[str, float],
) -> ScalingRunRecord:
    mutation = MutationSummary(
        requested_changed_sessions=size,
        actual_changed_sessions=size,
        added_sessions=1,
        removed_sessions=1,
        modified_session_ids=[f"s{i}" for i in range(size)],
        added_session_ids=["added"],
        removed_session_ids=["removed"],
        seed=1234,
    )
    return ScalingRunRecord(
        requested_changed_sessions=size,
        actual_changed_sessions=size,
        run_number=run_number,
        mutation=mutation,
        benchmark=make_benchmark(total_ms=total_ms, timings=timings),
    )


# ---------------------------------------------------------------------------
# -- Start-time mutation maths
# ---------------------------------------------------------------------------


@mark.parametrize(
    ("minutes", "expected"),
    [(0, 0), (510, 830), (540, 900), (600, 1000), (1290, 2130)],
)
def test_minutes_to_hhmm(minutes: int, expected: int) -> None:
    assert _minutes_to_hhmm(minutes) == expected


@mark.parametrize(
    ("start_time", "step", "expected"),
    [
        (830, 0, 900),  # +30 min
        (830, 1, 930),  # +60 min
        (1000, 2, 1030),  # even step -> +30
    ],
)
def test_shift_start_time_moves_forward(start_time: int, step: int, expected: int) -> None:
    assert _shift_start_time(start_time, step) == expected


def test_shift_start_time_wraps_backwards_past_late_evening() -> None:
    # 22:00 + 30 exceeds the 22:00 ceiling, so it shifts backwards instead.
    assert _shift_start_time(2200, 0) == 2130


def test_shift_start_time_always_changes_the_value() -> None:
    for start in (800, 830, 900, 1000, 1200, 1800):
        for step in range(4):
            assert _shift_start_time(start, step) != start


# ---------------------------------------------------------------------------
# -- percentile_nearest_rank
# ---------------------------------------------------------------------------


def test_percentile_nearest_rank_empty_is_zero() -> None:
    assert percentile_nearest_rank([], 90) == 0.0


@mark.parametrize(
    ("percentile", "expected"),
    [(50, 2.0), (90, 4.0), (100, 4.0), (25, 1.0)],
)
def test_percentile_nearest_rank(percentile: float, expected: float) -> None:
    assert percentile_nearest_rank([4.0, 1.0, 3.0, 2.0], percentile) == expected


# ---------------------------------------------------------------------------
# -- phase timing aggregation
# ---------------------------------------------------------------------------


def test_median_phase_timings_medians_across_records() -> None:
    records = [
        make_record(size=5, run_number=1, total_ms=10, timings={"build": 4.0, "conflicts": 2.0}),
        make_record(size=5, run_number=2, total_ms=12, timings={"build": 6.0, "conflicts": 2.0}),
        make_record(size=5, run_number=3, total_ms=14, timings={"build": 8.0}),
    ]
    medians = median_phase_timings(records)
    assert medians["build"] == 6.0
    # Missing phase entries count as 0.0 for the median.
    assert medians["conflicts"] == 2.0


def test_dominant_phase_is_slowest_median() -> None:
    records = [
        make_record(size=5, run_number=1, total_ms=10, timings={"build": 8.0, "conflicts": 2.0}),
    ]
    assert dominant_phase(records) == "build"


def test_dominant_phase_na_when_no_timings() -> None:
    records = [make_record(size=5, run_number=1, total_ms=10, timings={})]
    assert dominant_phase(records) == "n/a"


# ---------------------------------------------------------------------------
# -- build_size_summary
# ---------------------------------------------------------------------------


def test_build_size_summary_core_fields() -> None:
    records = [
        make_record(size=5, run_number=1, total_ms=10, timings={"build": 6.0}),
        make_record(size=5, run_number=2, total_ms=20, timings={"build": 8.0}),
    ]
    summary = build_size_summary(5, records)
    assert summary["requested_changed_sessions"] == 5
    assert summary["actual_changed_sessions"] == [5]
    assert summary["runs"] == 2
    assert summary["median_total_ms"] == 15.0
    assert summary["dominant_phase"] == "build"
    assert summary["ms_per_changed_session"] == 3.0
    assert summary["delta_vs_previous_ms"] is None


def test_build_size_summary_computes_delta_vs_previous() -> None:
    previous = build_size_summary(
        5,
        [make_record(size=5, run_number=1, total_ms=10, timings={"build": 6.0})],
    )
    current = build_size_summary(
        10,
        [make_record(size=10, run_number=1, total_ms=25, timings={"build": 15.0})],
        previous,
    )
    assert current["delta_vs_previous_ms"] == 15.0
    assert current["fastest_growing_phase"] == "build"


# ---------------------------------------------------------------------------
# -- linear_fit_estimate & doubling_ratios
# ---------------------------------------------------------------------------


def test_linear_fit_estimate_recovers_line() -> None:
    fit = linear_fit_estimate([(1, 3.0), (2, 5.0), (3, 7.0)])
    assert fit is not None
    assert fit["slope_ms_per_changed_session"] == approx(2.0)
    assert fit["intercept_ms"] == approx(1.0)


def test_linear_fit_estimate_none_for_insufficient_points() -> None:
    assert linear_fit_estimate([(1, 3.0)]) is None


def test_linear_fit_estimate_none_for_vertical_points() -> None:
    assert linear_fit_estimate([(5, 1.0), (5, 2.0)]) is None


def test_doubling_ratios_matches_sizes_and_their_doubles() -> None:
    summaries = [
        {"requested_changed_sessions": 5, "median_total_ms": 10.0},
        {"requested_changed_sessions": 10, "median_total_ms": 25.0},
    ]
    ratios = doubling_ratios(summaries)
    assert ratios == [
        {"from_changed_sessions": 5, "to_changed_sessions": 10, "runtime_ratio": 2.5},
    ]


def test_doubling_ratios_empty_when_no_double_present() -> None:
    summaries = [{"requested_changed_sessions": 5, "median_total_ms": 10.0}]
    assert doubling_ratios(summaries) == []


# ---------------------------------------------------------------------------
# -- dataclass serialization
# ---------------------------------------------------------------------------


def test_mutation_summary_to_dict_round_trips_fields() -> None:
    mutation = MutationSummary(
        requested_changed_sessions=3,
        actual_changed_sessions=3,
        added_sessions=1,
        removed_sessions=0,
        modified_session_ids=["a", "b", "c"],
        added_session_ids=["d"],
        removed_session_ids=[],
        seed=99,
    )
    as_dict = mutation.to_dict()
    assert as_dict["requested_changed_sessions"] == 3
    assert as_dict["modified_session_ids"] == ["a", "b", "c"]
    assert as_dict["seed"] == 99


def test_scaling_run_record_to_dict_nests_mutation_and_benchmark() -> None:
    record = make_record(size=5, run_number=2, total_ms=10, timings={"build": 6.0})
    as_dict = record.to_dict()
    assert as_dict["run_number"] == 2
    assert as_dict["mutation"]["seed"] == 1234
    assert as_dict["benchmark"]["total_ms"] == 10


# ---------------------------------------------------------------------------
# -- artifact assembly & serialization
# ---------------------------------------------------------------------------


def test_build_scaling_artifact_includes_summaries_and_fit() -> None:
    records = [
        make_record(size=5, run_number=1, total_ms=10, timings={"build": 6.0}),
        make_record(size=10, run_number=1, total_ms=20, timings={"build": 12.0}),
    ]
    artifact = build_scaling_artifact(
        source_project="project_id:1",
        source_project_dir=Path("/tmp/project"),
        sizes=[5, 10],
        repetitions=1,
        seed=1234,
        recalculate=True,
        payload_format="compact",
        records=records,
        git_commit="abc123",
    )
    assert len(artifact["summaries"]) == 2
    assert artifact["git_commit"] == "abc123"
    assert artifact["linear_fit"] is not None
    assert artifact["doubling_ratios"][0]["from_changed_sessions"] == 5


def test_write_scaling_artifacts_writes_json_and_csv(tmp_path: Path) -> None:
    records = [make_record(size=5, run_number=1, total_ms=10, timings={"build": 6.0})]
    artifact = build_scaling_artifact(
        source_project="project_id:1",
        source_project_dir=Path("/tmp/project"),
        sizes=[5],
        repetitions=1,
        seed=1234,
        recalculate=True,
        payload_format="compact",
        records=records,
        git_commit=None,
    )

    json_path, csv_path = write_scaling_artifacts(artifact, tmp_path / "artifacts")

    assert json_path.exists()
    assert csv_path.exists()
    loaded = json.loads(json_path.read_text(encoding="utf-8"))
    assert "runs" in loaded
    assert "summaries" in loaded
    csv_text = csv_path.read_text(encoding="utf-8")
    assert "requested_changed_sessions" in csv_text
    assert "median_total_ms" in csv_text
