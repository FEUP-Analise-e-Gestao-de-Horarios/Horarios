from __future__ import annotations

import csv
import json
import shutil
import uuid
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from random import Random
from statistics import median
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.exporter.benchmark_runtime import ExportBenchmarkResult, general_db_path, initial_db_path
from src.exporter.export_graph_utils import convert_to_minutes
from src.projects.projects_db.dao.export_cache_dao import ExportCacheDAO
from src.projects.projects_db.dao.modified_session_dao import ModifiedSessionDAO
from src.projects.projects_db.dao.session_dao import SessionDAO
from src.projects.projects_db.models.room import Room
from src.projects.projects_db.models.session import Session
from src.projects.projects_db.models.session_class_subject import SessionClassSubject
from src.projects.projects_db.models.teacher import Teacher
from src.projects.projects_db.registry import evict_engine, get_session

DEFAULT_BENCHMARK_SEED = 20260702


@dataclass(frozen=True)
class MutationSummary:
    requested_changed_sessions: int
    actual_changed_sessions: int
    added_sessions: int
    removed_sessions: int
    modified_session_ids: list[str]
    added_session_ids: list[str]
    removed_session_ids: list[str]
    seed: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ScalingRunRecord:
    requested_changed_sessions: int
    actual_changed_sessions: int
    run_number: int
    mutation: MutationSummary
    benchmark: ExportBenchmarkResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "requested_changed_sessions": self.requested_changed_sessions,
            "actual_changed_sessions": self.actual_changed_sessions,
            "run_number": self.run_number,
            "mutation": self.mutation.to_dict(),
            "benchmark": self.benchmark.to_dict(),
        }


def copy_project_tree(
    source_project_dir: Path,
    destination_projects_root: Path,
    project_id: int,
) -> Path:
    destination = destination_projects_root / str(project_id)
    shutil.rmtree(destination, ignore_errors=True)
    shutil.copytree(source_project_dir, destination)
    return destination


def count_changed_sessions(project_id: int, *, projects_db_path: Path | None = None) -> int:
    general_path = general_db_path(project_id, projects_db_path)
    initial_path = initial_db_path(project_id, projects_db_path)

    with get_session(general_path) as session:
        session_dao = SessionDAO(session)
        alias = session_dao.attach_db(initial_path)
        try:
            return len(session_dao.get_changes_only(alias))
        finally:
            session_dao.detach_db(alias)


def ensure_clean_exporter_baseline(
    project_id: int,
    *,
    projects_db_path: Path | None = None,
) -> None:
    general_path = general_db_path(project_id, projects_db_path)
    initial_path = initial_db_path(project_id, projects_db_path)
    ensure_clean_exporter_baseline_paths(general_path, initial_path)


def ensure_clean_exporter_baseline_paths(general_path: Path, initial_path: Path) -> None:
    if not general_path.exists() or not initial_path.exists():
        raise ValueError("Both general and initial database files must exist for benchmarking.")

    with get_session(general_path) as session:
        session_dao = SessionDAO(session)
        alias = session_dao.attach_db(initial_path)
        try:
            changes = session_dao.get_changes_only(alias)
            added_removed = session_dao.get_added_removed_records(alias)
        finally:
            session_dao.detach_db(alias)

    if changes or added_removed["added"] or added_removed["removed"]:
        raise ValueError(
            "Seed project must start with matching initial/general databases so the benchmark "
            "can produce exact changed-session counts.",
        )


def _minutes_to_hhmm(minutes: int) -> int:
    hours, mins = divmod(minutes, 60)
    return hours * 100 + mins


def _shift_start_time(start_time: int, step: int) -> int:
    minutes = convert_to_minutes(start_time)
    delta = 30 * (1 + (step % 2))
    shifted = minutes + delta
    if shifted > 22 * 60:
        shifted = max(7 * 60, minutes - delta)
    if shifted == minutes:
        shifted = minutes + 30
    return _minutes_to_hhmm(shifted)


def _stable_uuid(rng: Random) -> uuid.UUID:
    return uuid.UUID(int=rng.getrandbits(128), version=4)


def _ordered_sessions(session) -> list[Session]:
    return list(
        session.scalars(
            select(Session)
            .join(SessionClassSubject)
            .distinct()
            .options(
                selectinload(Session.rooms),
                selectinload(Session.teachers),
                selectinload(Session.session_class_subjects).joinedload(SessionClassSubject.class_),
                selectinload(Session.session_class_subjects).joinedload(
                    SessionClassSubject.subject,
                ),
            )
            .order_by(Session.week, Session.weekday, Session.start_time, Session.id),
        ).unique(),
    )


def _replace_room(session_obj: Session, rooms: list[Room]) -> bool:
    current_ids = {room.id for room in session_obj.rooms}
    replacement = next((room for room in rooms if room.id not in current_ids), None)
    if replacement is None or not session_obj.rooms:
        return False

    updated_rooms = list(session_obj.rooms)
    updated_rooms[0] = replacement
    session_obj.rooms = updated_rooms
    return True


def _replace_teacher(session_obj: Session, teachers: list[Teacher]) -> bool:
    current_ids = {teacher.id for teacher in session_obj.teachers}
    replacement = next((teacher for teacher in teachers if teacher.id not in current_ids), None)
    if replacement is None or not session_obj.teachers:
        return False

    updated_teachers = list(session_obj.teachers)
    updated_teachers[0] = replacement
    session_obj.teachers = updated_teachers
    return True


def _clone_session(source: Session, rng: Random, index: int) -> Session:
    return Session(
        id=_stable_uuid(rng),
        week=source.week,
        weekday=source.weekday,
        start_time=_shift_start_time(int(source.start_time), index + 1),
        duration=source.duration,
        type=source.type,
        original_block_id=_stable_uuid(rng),
        rooms=list(source.rooms),
        teachers=list(source.teachers),
        session_class_subjects=[
            SessionClassSubject(class_=relation.class_, subject=relation.subject)
            for relation in source.session_class_subjects
        ],
    )


def mutate_project_for_benchmark(
    project_id: int,
    *,
    changed_sessions: int,
    seed: int = DEFAULT_BENCHMARK_SEED,
    projects_db_path: Path | None = None,
) -> MutationSummary:
    if changed_sessions < 0:
        raise ValueError("changed_sessions must be non-negative")

    general_path = general_db_path(project_id, projects_db_path)
    rng = Random(seed)

    with get_session(general_path) as session:
        sessions = _ordered_sessions(session)
        if changed_sessions > len(sessions):
            raise ValueError(
                f"Requested {changed_sessions} changed sessions, but only {len(sessions)} eligible sessions exist.",
            )

        rooms = list(session.scalars(select(Room).order_by(Room.name, Room.id)).all())
        teachers = list(session.scalars(select(Teacher).order_by(Teacher.number, Teacher.id)).all())
        modified_sessions = rng.sample(sessions, changed_sessions) if changed_sessions else []
        modified_ids = {session_obj.id for session_obj in modified_sessions}
        remaining_sessions = [
            session_obj for session_obj in sessions if session_obj.id not in modified_ids
        ]

        for index, session_obj in enumerate(modified_sessions):
            session_obj.start_time = _shift_start_time(int(session_obj.start_time), index)
            if index % 2 == 0:
                _replace_room(session_obj, rooms)
            if index % 3 == 0:
                _replace_teacher(session_obj, teachers)

        added_session_ids: list[str] = []
        removed_session_ids: list[str] = []
        if changed_sessions > 0 and remaining_sessions:
            add_source = remaining_sessions[0]
            added_session = _clone_session(add_source, rng, changed_sessions)
            session.add(added_session)
            added_session_ids.append(str(added_session.id))

            removable = next(
                (
                    session_obj
                    for session_obj in remaining_sessions[1:]
                    if session_obj.id != add_source.id
                ),
                None,
            )
            if removable is not None:
                removable.rooms.clear()
                removable.teachers.clear()
                session.delete(removable)
                removed_session_ids.append(str(removable.id))

        ExportCacheDAO(session).clear_project_export_payload()
        ModifiedSessionDAO(session).clear_modification_steps()
        session.commit()

    actual_changed_sessions = count_changed_sessions(project_id, projects_db_path=projects_db_path)
    return MutationSummary(
        requested_changed_sessions=changed_sessions,
        actual_changed_sessions=actual_changed_sessions,
        added_sessions=len(added_session_ids),
        removed_sessions=len(removed_session_ids),
        modified_session_ids=sorted(str(session_id) for session_id in modified_ids),
        added_session_ids=sorted(added_session_ids),
        removed_session_ids=sorted(removed_session_ids),
        seed=seed,
    )


def percentile_nearest_rank(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    rank = max(1, int((percentile / 100) * len(ordered) + 0.999999))
    return ordered[min(rank - 1, len(ordered) - 1)]


def median_phase_timings(records: list[ScalingRunRecord]) -> dict[str, float]:
    phase_names = {name for record in records for name in record.benchmark.timings_ms}
    return {
        phase: round(
            median([record.benchmark.timings_ms.get(phase, 0.0) for record in records]),
            2,
        )
        for phase in sorted(phase_names)
    }


def dominant_phase(records: list[ScalingRunRecord]) -> str:
    phase_medians = median_phase_timings(records)
    if not phase_medians:
        return "n/a"
    return max(phase_medians, key=phase_medians.get)


def build_size_summary(
    size: int,
    records: list[ScalingRunRecord],
    previous_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    total_values = [record.benchmark.total_ms for record in records]
    median_total_ms = round(median(total_values), 2)
    phase_medians = median_phase_timings(records)
    summary = {
        "requested_changed_sessions": size,
        "actual_changed_sessions": sorted({record.actual_changed_sessions for record in records}),
        "runs": len(records),
        "median_total_ms": median_total_ms,
        "p90_total_ms": round(percentile_nearest_rank(total_values, 90), 2),
        "median_response_payload_kb": round(
            median([record.benchmark.response_payload_kb for record in records]),
            2,
        ),
        "median_payload_kb": {
            "compact": round(
                median([record.benchmark.payload_kb["compact"] for record in records]),
                2,
            ),
            "expanded": round(
                median([record.benchmark.payload_kb["expanded"] for record in records]),
                2,
            ),
        },
        "median_phase_timings_ms": phase_medians,
        "dominant_phase": dominant_phase(records),
        "ms_per_changed_session": round(median_total_ms / size, 2) if size else 0.0,
        "delta_vs_previous_ms": None,
        "fastest_growing_phase": None,
    }
    if previous_summary is not None:
        summary["delta_vs_previous_ms"] = round(
            median_total_ms - float(previous_summary["median_total_ms"]),
            2,
        )
        previous_phases = previous_summary["median_phase_timings_ms"]
        if phase_medians:
            summary["fastest_growing_phase"] = max(
                phase_medians,
                key=lambda phase: phase_medians.get(phase, 0.0) - previous_phases.get(phase, 0.0),
            )
    return summary


def linear_fit_estimate(points: list[tuple[int, float]]) -> dict[str, float] | None:
    if len(points) < 2:
        return None
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator == 0:
        return None
    slope = sum((x - mean_x) * (y - mean_y) for x, y in points) / denominator
    intercept = mean_y - slope * mean_x
    return {
        "slope_ms_per_changed_session": round(slope, 4),
        "intercept_ms": round(intercept, 4),
    }


def doubling_ratios(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_size = {int(summary["requested_changed_sessions"]): summary for summary in summaries}
    ratios = []
    for size, summary in sorted(by_size.items()):
        doubled = size * 2
        if size == 0 or doubled not in by_size:
            continue
        doubled_summary = by_size[doubled]
        ratio = (
            float(doubled_summary["median_total_ms"]) / float(summary["median_total_ms"])
            if float(summary["median_total_ms"]) > 0
            else 0.0
        )
        ratios.append(
            {
                "from_changed_sessions": size,
                "to_changed_sessions": doubled,
                "runtime_ratio": round(ratio, 3),
            },
        )
    return ratios


def build_scaling_artifact(
    *,
    source_project: str,
    source_project_dir: Path,
    sizes: list[int],
    repetitions: int,
    seed: int,
    recalculate: bool,
    payload_format: str,
    records: list[ScalingRunRecord],
    git_commit: str | None,
) -> dict[str, Any]:
    records_by_size: dict[int, list[ScalingRunRecord]] = {}
    for record in records:
        records_by_size.setdefault(record.requested_changed_sessions, []).append(record)

    summaries: list[dict[str, Any]] = []
    previous_summary: dict[str, Any] | None = None
    for size in sizes:
        size_records = records_by_size.get(size, [])
        if not size_records:
            continue
        summary = build_size_summary(size, size_records, previous_summary)
        summaries.append(summary)
        previous_summary = summary

    fit = linear_fit_estimate(
        [
            (int(summary["requested_changed_sessions"]), float(summary["median_total_ms"]))
            for summary in summaries
        ],
    )
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_project": source_project,
        "source_project_dir": str(source_project_dir),
        "sizes": sizes,
        "repetitions": repetitions,
        "seed": seed,
        "recalculate": recalculate,
        "payload_format": payload_format,
        "git_commit": git_commit,
        "runs": [record.to_dict() for record in records],
        "summaries": summaries,
        "doubling_ratios": doubling_ratios(summaries),
        "linear_fit": fit,
    }


def write_scaling_artifacts(artifact: dict[str, Any], output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    json_path = output_dir / f"exporter-scaling-{timestamp}.json"
    csv_path = output_dir / f"exporter-scaling-summary-{timestamp}.csv"

    json_path.write_text(json.dumps(artifact, indent=2), encoding="utf-8")

    summaries = artifact["summaries"]
    phase_names = sorted(
        {phase for summary in summaries for phase in summary["median_phase_timings_ms"]},
    )
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "requested_changed_sessions",
                "actual_changed_sessions",
                "runs",
                "median_total_ms",
                "p90_total_ms",
                "median_response_payload_kb",
                "median_compact_payload_kb",
                "median_expanded_payload_kb",
                "dominant_phase",
                "delta_vs_previous_ms",
                "fastest_growing_phase",
                "ms_per_changed_session",
                *[f"median_phase_{phase}_ms" for phase in phase_names],
            ],
        )
        writer.writeheader()
        for summary in summaries:
            row = {
                "requested_changed_sessions": summary["requested_changed_sessions"],
                "actual_changed_sessions": ",".join(
                    str(value) for value in summary["actual_changed_sessions"]
                ),
                "runs": summary["runs"],
                "median_total_ms": summary["median_total_ms"],
                "p90_total_ms": summary["p90_total_ms"],
                "median_response_payload_kb": summary["median_response_payload_kb"],
                "median_compact_payload_kb": summary["median_payload_kb"]["compact"],
                "median_expanded_payload_kb": summary["median_payload_kb"]["expanded"],
                "dominant_phase": summary["dominant_phase"],
                "delta_vs_previous_ms": summary["delta_vs_previous_ms"],
                "fastest_growing_phase": summary["fastest_growing_phase"],
                "ms_per_changed_session": summary["ms_per_changed_session"],
            }
            row.update(
                {
                    f"median_phase_{phase}_ms": summary["median_phase_timings_ms"].get(phase, 0.0)
                    for phase in phase_names
                },
            )
            writer.writerow(row)
    return json_path, csv_path


def print_size_summary(summary: dict[str, Any]) -> None:
    delta = summary["delta_vs_previous_ms"]
    delta_text = f"{delta:+.2f} ms" if delta is not None else "n/a"
    print(
        f"size={summary['requested_changed_sessions']} "
        f"median={summary['median_total_ms']:.2f} ms "
        f"delta={delta_text} "
        f"dominant_phase={summary['dominant_phase']}",
    )
    if summary["fastest_growing_phase"] is not None:
        print(f"  fastest_growing_phase={summary['fastest_growing_phase']}")


def print_growth_diagnostics(artifact: dict[str, Any]) -> None:
    if artifact["linear_fit"] is not None:
        fit = artifact["linear_fit"]
        print(
            "linear_fit="
            f"{fit['intercept_ms']:.2f} ms + "
            f"{fit['slope_ms_per_changed_session']:.2f} ms/session",
        )
    for ratio in artifact["doubling_ratios"]:
        print(
            "doubling_ratio="
            f"{ratio['from_changed_sessions']}->{ratio['to_changed_sessions']} "
            f"{ratio['runtime_ratio']:.3f}x",
        )


def cleanup_project_tree(project_dir: Path) -> None:
    for db_name in ("general_database.db", "initial_database.db"):
        evict_engine(project_dir / db_name)
    shutil.rmtree(project_dir, ignore_errors=True)
