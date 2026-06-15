#!/usr/bin/env python3
"""Measure exporter generation phases for a project database."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from time import perf_counter


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_id", type=int)
    parser.add_argument(
        "--backend-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "backend",
    )
    parser.add_argument(
        "--projects-db-path",
        type=Path,
        help="Override the project database root, useful for benchmarking copied DBs.",
    )
    args = parser.parse_args()

    sys.path.insert(0, str(args.backend_dir))
    os.environ.setdefault("SECRET_KEY", "benchmark-secret-key")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "src.config.settings.dev")

    import django

    django.setup()

    if args.projects_db_path is not None:
        from django.conf import settings

        settings.PROJECTS_DB_PATH = args.projects_db_path

    from src.core.schemas import SuccessResponse
    from src.exporter.compact_payload import compact_export_payload
    from src.exporter.export_graph import ExportGraph
    from src.projects.projects_db.dao.class_dao import ClassDAO
    from src.projects.projects_db.dao.room_dao import RoomDAO
    from src.projects.projects_db.dao.session_dao import SessionDAO
    from src.projects.projects_db.dao.teacher_dao import TeacherDAO
    from src.projects.projects_db.paths import general_db, initial_db
    from src.projects.projects_db.registry import get_session, init_engine

    timings: list[tuple[str, float]] = []

    def measure[T](label: str, fn) -> T:
        start = perf_counter()
        result = fn()
        timings.append((label, perf_counter() - start))
        return result

    project_id = args.project_id
    measure("init_engine", lambda: init_engine(general_db(project_id)))

    with get_session(general_db(project_id)) as session:
        session_dao = SessionDAO(session)
        rooms_dao = RoomDAO(session)
        teachers_dao = TeacherDAO(session)
        class_dao = ClassDAO(session)

        alias = measure("attach_initial_db", lambda: session_dao.attach_db(initial_db(project_id)))
        added_removed = measure(
            "added_removed_sessions",
            lambda: session_dao.get_added_removed_records(alias),
        )
        rooms_conflicts = measure("room_conflicts", rooms_dao.get_conflicting_slots)
        teacher_conflicts = measure("teacher_conflicts", teachers_dao.get_conflicting_slots)
        classes_conflicts = measure("class_conflicts", class_dao.get_conflicting_slots)
        changes = measure("changes_only", lambda: session_dao.get_changes_only(alias))
        measure("detach_initial_db", lambda: session_dao.detach_db(alias))

    export_graph = measure("export_graph_init", lambda: ExportGraph(changes, project_id))
    modification_steps = measure("build_modification_steps", export_graph.build_modification_steps)
    expanded_payload = {
        "added_removed_sessions": added_removed,
        "rooms_conflicts": rooms_conflicts,
        "teacher_conflicts": teacher_conflicts,
        "classes_conflicts": classes_conflicts,
        "modification_steps": modification_steps,
    }
    expanded_body = measure(
        "expanded_json_dump",
        lambda: json.dumps(
            SuccessResponse(message="ok", data=expanded_payload).model_dump(),
            default=str,
        ),
    )
    compact_payload = measure("compact_payload_build", lambda: compact_export_payload(expanded_payload))
    compact_body = measure(
        "compact_json_dump",
        lambda: json.dumps(
            SuccessResponse(message="ok", data=compact_payload).model_dump(),
            default=str,
        ),
    )

    print(
        json.dumps(
            {
                "project_id": project_id,
                "counts": {
                    "changed_sessions": len(changes),
                    "modification_steps": len(modification_steps),
                    "room_conflicts": len(rooms_conflicts),
                    "teacher_conflicts": len(teacher_conflicts),
                    "class_conflicts": len(classes_conflicts),
                },
                "payload_kb": {
                    "expanded": round(len(expanded_body) / 1024, 1),
                    "compact": round(len(compact_body) / 1024, 1),
                },
                "timings_ms": {
                    label: round(duration * 1000, 2)
                    for label, duration in timings
                },
                "total_ms": round(sum(duration for _, duration in timings) * 1000, 2),
            },
            indent=2,
        ),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
