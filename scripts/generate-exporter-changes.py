#!/usr/bin/env python3
"""Create artificial exporter-visible changes in a project database.

The exporter compares a project's ``general_database.db`` against its
``initial_database.db``. This script mutates only the general database so the
exporter can report realistic added, removed, and modified sessions.

Examples:
    python3 scripts/generate-exporter-changes.py --project-id 1
    python3 scripts/generate-exporter-changes.py --db databases/projects/1/general_database.db
    python3 scripts/generate-exporter-changes.py --project-id 1 --dry-run
"""

from __future__ import annotations

import argparse
import shutil
import sqlite3
import sys
import uuid
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PROJECTS_DB_DIR = ROOT_DIR / "databases" / "projects"


class ScriptError(RuntimeError):
    """User-facing script error."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Mutate a project's general_database.db so the exporter detects "
            "added, removed, and modified sessions."
        ),
    )
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--project-id", type=int, help="Project id under databases/projects/<id>.")
    target.add_argument("--db", type=Path, help="Path to a general_database.db file.")
    parser.add_argument(
        "--projects-db-dir",
        type=Path,
        default=DEFAULT_PROJECTS_DB_DIR,
        help=f"Projects DB root used with --project-id. Default: {DEFAULT_PROJECTS_DB_DIR}",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the planned changes without writing them.",
    )
    parser.add_argument(
        "--backup",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Create a .bak file before writing. Enabled by default.",
    )
    return parser.parse_args()


def resolve_db_path(args: argparse.Namespace) -> Path:
    if args.db:
        return args.db.expanduser().resolve()

    return (args.projects_db_dir / str(args.project_id) / "general_database.db").resolve()


def connect(db_path: Path) -> sqlite3.Connection:
    if not db_path.exists():
        raise ScriptError(f"Database not found: {db_path}")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def require_tables(conn: sqlite3.Connection) -> None:
    required = {
        "sessions",
        "session_rooms",
        "session_teachers",
        "sessions_classes_subject",
        "rooms",
        "teachers",
        "modified_sessions",
    }
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    existing = {row["name"] for row in rows}
    missing = sorted(required - existing)
    if missing:
        raise ScriptError(f"Database is missing required tables: {', '.join(missing)}")


def fetch_sessions(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return list(
        conn.execute(
            """
            SELECT s.*
            FROM sessions AS s
            WHERE EXISTS (
                SELECT 1
                FROM sessions_classes_subject AS scs
                WHERE scs.session_id = s.id
            )
            ORDER BY s.week, s.weekday, s.start_time, s.id
            """,
        ).fetchall(),
    )


def shift_time(hhmm: int) -> int:
    minutes = (hhmm // 100) * 60 + (hhmm % 100)
    shifted = minutes + 30 if minutes < 19 * 60 else minutes - 30
    return (shifted // 60) * 100 + (shifted % 60)


def fetch_record_ids(conn: sqlite3.Connection, table: str) -> list[str]:
    return [row["id"] for row in conn.execute(f"SELECT id FROM {table}").fetchall()]


def fetch_session_relation_ids(
    conn: sqlite3.Connection,
    table: str,
    id_column: str,
    session_id: str,
) -> list[str]:
    return [
        row[id_column]
        for row in conn.execute(
            f"SELECT {id_column} FROM {table} WHERE session_id = ?",
            (session_id,),
        ).fetchall()
    ]


def swap_first_available_relation(
    conn: sqlite3.Connection,
    *,
    session_id: str,
    relation_table: str,
    related_table: str,
    id_column: str,
    dry_run: bool,
) -> str | None:
    current_ids = fetch_session_relation_ids(conn, relation_table, id_column, session_id)
    all_ids = fetch_record_ids(conn, related_table)
    replacement_id = next((id_ for id_ in all_ids if id_ not in current_ids), None)
    if not current_ids or replacement_id is None:
        return None

    removed_id = current_ids[0]
    if not dry_run:
        conn.execute(
            f"DELETE FROM {relation_table} WHERE session_id = ? AND {id_column} = ?",
            (session_id, removed_id),
        )
        conn.execute(
            f"INSERT OR IGNORE INTO {relation_table} (session_id, {id_column}) VALUES (?, ?)",
            (session_id, replacement_id),
        )

    return f"{relation_table}: replaced one relation"


def copy_relations(conn: sqlite3.Connection, source_id: str, target_id: str) -> None:
    for table, columns in (
        ("session_rooms", ("room_id",)),
        ("session_teachers", ("teacher_id",)),
        ("sessions_classes_subject", ("class_id", "subject_id")),
    ):
        select_cols = ", ".join(columns)
        rows = conn.execute(
            f"SELECT {select_cols} FROM {table} WHERE session_id = ?",
            (source_id,),
        ).fetchall()
        for row in rows:
            col_names = ("session_id", *columns)
            placeholders = ", ".join("?" for _ in col_names)
            values = (target_id, *(row[column] for column in columns))
            conn.execute(
                f"INSERT INTO {table} ({', '.join(col_names)}) VALUES ({placeholders})",
                values,
            )


def add_session_copy(
    conn: sqlite3.Connection,
    source: sqlite3.Row,
    *,
    dry_run: bool,
) -> str:
    new_id = str(uuid.uuid4())
    new_block_id = str(uuid.uuid4())
    if not dry_run:
        conn.execute(
            """
            INSERT INTO sessions (
                id, week, weekday, start_time, duration, type, original_block_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id,
                source["week"],
                source["weekday"],
                shift_time(int(source["start_time"])),
                source["duration"],
                source["type"],
                new_block_id,
            ),
        )
        copy_relations(conn, source["id"], new_id)

    return f"added a copy of {session_label(source)}"


def delete_session(conn: sqlite3.Connection, session: sqlite3.Row, *, dry_run: bool) -> str:
    if not dry_run:
        for table in ("session_rooms", "session_teachers", "sessions_classes_subject"):
            conn.execute(f"DELETE FROM {table} WHERE session_id = ?", (session["id"],))
        conn.execute("DELETE FROM sessions WHERE id = ?", (session["id"],))

    return f"removed {session_label(session)}"


def session_label(session: sqlite3.Row) -> str:
    return (
        f"{session['week']} {session['weekday']} "
        f"{session['start_time']} ({session['type']})"
    )


def mutate(conn: sqlite3.Connection, *, dry_run: bool) -> list[str]:
    sessions = fetch_sessions(conn)
    if not sessions:
        raise ScriptError("No sessions with class/subject relations were found.")

    planned: list[str] = []
    modify_session = sessions[0]
    add_source = sessions[1] if len(sessions) > 1 else sessions[0]
    remove_session = sessions[2] if len(sessions) > 2 else None

    old_time = int(modify_session["start_time"])
    new_time = shift_time(old_time)
    if not dry_run:
        conn.execute(
            "UPDATE sessions SET start_time = ? WHERE id = ?",
            (new_time, modify_session["id"]),
        )
    planned.append(f"moved {session_label(modify_session)} from {old_time} to {new_time}")

    for relation in (
        ("session_rooms", "rooms", "room_id"),
        ("session_teachers", "teachers", "teacher_id"),
    ):
        result = swap_first_available_relation(
            conn,
            session_id=modify_session["id"],
            relation_table=relation[0],
            related_table=relation[1],
            id_column=relation[2],
            dry_run=dry_run,
        )
        if result:
            planned.append(f"{result} on modified session")

    planned.append(add_session_copy(conn, add_source, dry_run=dry_run))

    if remove_session is not None:
        planned.append(delete_session(conn, remove_session, dry_run=dry_run))
    else:
        planned.append("skipped removal because the database has fewer than 3 suitable sessions")

    if not dry_run:
        conn.execute("DELETE FROM modified_sessions")
    planned.append("cleared cached exporter modification steps")

    return planned


def make_backup(db_path: Path) -> Path:
    backup_path = db_path.with_suffix(f"{db_path.suffix}.bak")
    shutil.copy2(db_path, backup_path)
    return backup_path


def main() -> int:
    args = parse_args()
    db_path = resolve_db_path(args)

    try:
        with connect(db_path) as conn:
            require_tables(conn)
            if args.backup and not args.dry_run:
                backup_path = make_backup(db_path)
                print(f"Backup written: {backup_path}")

            planned = mutate(conn, dry_run=args.dry_run)
            if args.dry_run:
                conn.rollback()
            else:
                conn.commit()

        print("Exporter test changes:")
        for item in planned:
            print(f"- {item}")
        print(f"Database: {db_path}")
        if args.dry_run:
            print("Dry run only; no changes were written.")
        return 0
    except (sqlite3.Error, ScriptError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
