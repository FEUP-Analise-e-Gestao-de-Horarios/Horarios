from __future__ import annotations

import json
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

from django.conf import settings

from src.core.schemas import SuccessResponse
from src.exporter.compact_payload import (
    COMPACT_EXPORT_FORMAT,
    compact_export_payload,
    expand_compact_export_payload,
)
from src.exporter.export_graph import ExportGraph
from src.exporter.schemas import (
    CompactProjectExportPayload,
    PayloadFormat,
    ProjectExportPayload,
)
from src.projects.projects_db.dao.class_dao import ClassDAO
from src.projects.projects_db.dao.export_cache_dao import ExportCacheDAO
from src.projects.projects_db.dao.modified_session_dao import ModifiedSessionDAO
from src.projects.projects_db.dao.room_dao import RoomDAO
from src.projects.projects_db.dao.session_dao import SessionDAO
from src.projects.projects_db.dao.teacher_dao import TeacherDAO
from src.projects.projects_db.registry import get_session, init_engine
from src.projects.views.export import ProjectExportView


@dataclass(frozen=True)
class BenchmarkCounts:
    changed_sessions: int
    modification_steps: int
    room_conflicts: int
    teacher_conflicts: int
    class_conflicts: int
    added_sessions: int
    removed_sessions: int


@dataclass(frozen=True)
class ExportBenchmarkResult:
    project_id: int
    projects_db_path: str | None
    recalculate: bool
    payload_format: PayloadFormat
    cache_hit: bool
    counts: BenchmarkCounts
    payload_kb: dict[str, float]
    response_payload_kb: float
    timings_ms: dict[str, float]
    total_ms: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def project_db_dir(project_id: int, projects_db_path: Path | None = None) -> Path:
    db_root = (
        Path(projects_db_path) if projects_db_path is not None else Path(settings.PROJECTS_DB_PATH)
    )
    return db_root / str(project_id)


def general_db_path(project_id: int, projects_db_path: Path | None = None) -> Path:
    return project_db_dir(project_id, projects_db_path) / "general_database.db"


def initial_db_path(project_id: int, projects_db_path: Path | None = None) -> Path:
    return project_db_dir(project_id, projects_db_path) / "initial_database.db"


@contextmanager
def override_projects_db_path(projects_db_path: Path | None):
    if projects_db_path is None:
        yield
        return

    original = Path(settings.PROJECTS_DB_PATH)
    settings.PROJECTS_DB_PATH = Path(projects_db_path)
    try:
        yield
    finally:
        settings.PROJECTS_DB_PATH = original


def _response_json_kb(payload: dict[str, Any], message: str) -> float:
    body = json.dumps(
        SuccessResponse(message=message, data=payload).model_dump(),
        default=str,
    )
    return round(len(body) / 1024, 1)


def _counts_from_payload(payload: ProjectExportPayload) -> BenchmarkCounts:
    unique_changed_sessions = {
        str(session_id) for step in payload.modification_steps for session_id in step.session_ids
    }
    return BenchmarkCounts(
        changed_sessions=len(unique_changed_sessions),
        modification_steps=len(payload.modification_steps),
        room_conflicts=len(payload.rooms_conflicts),
        teacher_conflicts=len(payload.teacher_conflicts),
        class_conflicts=len(payload.classes_conflicts),
        added_sessions=len(payload.added_removed_sessions.added),
        removed_sessions=len(payload.added_removed_sessions.removed),
    )


def _model_payload_from_cache(data: dict[str, Any]) -> ProjectExportPayload:
    if data.get("format") == COMPACT_EXPORT_FORMAT:
        return expand_compact_export_payload(CompactProjectExportPayload.model_validate(data))
    return ProjectExportPayload.model_validate(data)


def run_export_benchmark(
    project_id: int,
    *,
    recalculate: bool = True,
    payload_format: PayloadFormat = "compact",
    projects_db_path: Path | None = None,
) -> ExportBenchmarkResult:
    timings: list[tuple[str, float]] = []

    def measure[T](label: str, fn) -> T:
        start = perf_counter()
        result = fn()
        timings.append((label, perf_counter() - start))
        return result

    with override_projects_db_path(projects_db_path):
        general_path = general_db_path(project_id, projects_db_path)
        initial_path = initial_db_path(project_id, projects_db_path)
        measure("init_engine", lambda: init_engine(general_path))

        with get_session(general_path) as session:
            export_cache_dao = measure("export_cache_dao_init", lambda: ExportCacheDAO(session))

            if not recalculate:
                cached_data = measure(
                    "export_cache_lookup",
                    export_cache_dao.get_project_export_payload,
                )
                if cached_data is not None and cached_data.get("format") == COMPACT_EXPORT_FORMAT:
                    expanded_payload = measure(
                        "expand_cached_payload",
                        lambda: _model_payload_from_cache(cached_data),
                    )
                    response_data = measure(
                        "response_format",
                        lambda: ProjectExportView.format_export_payload(
                            cached_data,
                            payload_format,
                        ),
                    )
                    response_payload_kb = measure(
                        "response_json_dump",
                        lambda: _response_json_kb(
                            response_data,
                            "Project export loaded from cache",
                        ),
                    )
                    compact_json_kb = round(
                        len(json.dumps(cached_data, default=str)) / 1024,
                        1,
                    )
                    expanded_json_kb = round(
                        len(json.dumps(expanded_payload.model_dump(mode="json"), default=str))
                        / 1024,
                        1,
                    )
                    timings_ms = {label: round(duration * 1000, 2) for label, duration in timings}
                    return ExportBenchmarkResult(
                        project_id=project_id,
                        projects_db_path=str(projects_db_path)
                        if projects_db_path is not None
                        else None,
                        recalculate=recalculate,
                        payload_format=payload_format,
                        cache_hit=True,
                        counts=_counts_from_payload(expanded_payload),
                        payload_kb={
                            "expanded": expanded_json_kb,
                            "compact": compact_json_kb,
                        },
                        response_payload_kb=response_payload_kb,
                        timings_ms=timings_ms,
                        total_ms=round(sum(duration for _, duration in timings) * 1000, 2),
                    )

                if cached_data is not None:
                    measure("clear_legacy_cache", export_cache_dao.clear_project_export_payload)
                    measure("cache_commit", session.commit)

            session_dao = SessionDAO(session)
            modified_session_dao = ModifiedSessionDAO(session)
            rooms_dao = RoomDAO(session)
            teachers_dao = TeacherDAO(session)
            class_dao = ClassDAO(session)
            cached_modification_steps = (
                []
                if recalculate
                else measure(
                    "modification_step_cache_lookup",
                    modified_session_dao.get_cached_modification_steps,
                )
            )

            alias = measure("attach_initial_db", lambda: session_dao.attach_db(initial_path))
            try:
                added_removed_sessions = measure(
                    "added_removed_sessions",
                    lambda: session_dao.get_added_removed_records(alias),
                )
                rooms_conflicts = measure("room_conflicts", rooms_dao.get_conflicting_slots)
                teacher_conflicts = measure("teacher_conflicts", teachers_dao.get_conflicting_slots)
                classes_conflicts = measure("class_conflicts", class_dao.get_conflicting_slots)

                if cached_modification_steps:
                    modifications = None
                    modification_steps = cached_modification_steps
                else:
                    modifications = measure(
                        "changes_only",
                        lambda: session_dao.get_changes_only(alias),
                    )
                    export_graph = measure(
                        "export_graph_init",
                        lambda: ExportGraph(modifications, project_id),
                    )
                    modification_steps = measure(
                        "build_modification_steps",
                        export_graph.build_modification_steps,
                    )
                    measure(
                        "cache_modification_steps",
                        lambda: modified_session_dao.replace_modification_steps(modification_steps),
                    )
            finally:
                measure("detach_initial_db", lambda: session_dao.detach_db(alias))

            expanded_payload = measure(
                "payload_validate",
                lambda: ProjectExportPayload.model_validate(
                    {
                        "added_removed_sessions": added_removed_sessions,
                        "rooms_conflicts": rooms_conflicts,
                        "teacher_conflicts": teacher_conflicts,
                        "classes_conflicts": classes_conflicts,
                        "modification_steps": modification_steps,
                    },
                ),
            )
            compact_payload_model = measure(
                "compact_payload_build",
                lambda: compact_export_payload(expanded_payload),
            )
            expanded_json_kb = measure(
                "expanded_json_dump",
                lambda: round(
                    len(json.dumps(expanded_payload.model_dump(mode="json"), default=str)) / 1024,
                    1,
                ),
            )
            compact_json_kb = measure(
                "compact_json_dump",
                lambda: round(
                    len(
                        json.dumps(
                            compact_payload_model.model_dump(mode="json"),
                            default=str,
                        ),
                    )
                    / 1024,
                    1,
                ),
            )
            measure(
                "export_cache_write",
                lambda: export_cache_dao.replace_project_export_payload(compact_payload_model),
            )
            measure("cache_commit", session.commit)

            response_data = measure(
                "response_format",
                lambda: ProjectExportView.format_export_payload(
                    compact_payload_model,
                    payload_format,
                ),
            )
            response_payload_kb = measure(
                "response_json_dump",
                lambda: _response_json_kb(response_data, "Project export computed successfully"),
            )

    timings_ms = {label: round(duration * 1000, 2) for label, duration in timings}
    return ExportBenchmarkResult(
        project_id=project_id,
        projects_db_path=str(projects_db_path) if projects_db_path is not None else None,
        recalculate=recalculate,
        payload_format=payload_format,
        cache_hit=False,
        counts=_counts_from_payload(expanded_payload),
        payload_kb={
            "expanded": expanded_json_kb,
            "compact": compact_json_kb,
        },
        response_payload_kb=response_payload_kb,
        timings_ms=timings_ms,
        total_ms=round(sum(duration for _, duration in timings) * 1000, 2),
    )
