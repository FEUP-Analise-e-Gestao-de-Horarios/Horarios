import sqlite3

from src.ingestion.schemas.misc import Time, WeekDay
from src.ingestion.schemas.teachers import TeacherPage


def ingest_teacher(cursor: sqlite3.Cursor, teacher: TeacherPage) -> None:
    """Insert a teacher record into the ``docentes`` table, ignoring duplicates.

    Args:
        cursor: Active SQLite cursor used to execute the INSERT statement.
        teacher: Teacher data to persist, including code, name, and acronym.
    """
    cursor.execute(
        "INSERT OR IGNORE INTO docentes (numeroMecanografico, nome, abreviacao) VALUES (?, ?, ?)",
        (teacher["code"], teacher["name"], teacher["acronym"]),
    )


def ingest_teacher_red_blocks(
    cursor: sqlite3.Cursor,
    teacher_code: str,
    time: Time,
    day: WeekDay,
) -> None:
    """Link an unavailability block to a teacher in the ``blocoDocente`` table.

    Looks up the ``blocosVermelhos`` row for the given time and day, then
    inserts a ``(block_id, teacher_code)`` pair into ``blocoDocente``,
    ignoring duplicates.

    Args:
        cursor: Active SQLite cursor used to execute the queries.
        teacher_code: Numeric code of the teacher to associate with the block.
        time: Time slot encoded as ``HHMM`` (e.g. ``900`` for 09:00).
        day: Day of the week for the unavailability block.

    Raises:
        ValueError: If no matching row exists in ``blocosVermelhos`` for the
            given ``time`` and ``day``.
    """
    result = cursor.execute(
        "SELECT id FROM blocosVermelhos WHERE hora=? AND diaSemana=?",
        (time, day),
    ).fetchone()

    if not result:
        raise ValueError(f"Red block not found in DB: hora={time}, diaSemana={day}")

    cursor.execute(
        "INSERT OR IGNORE INTO blocoDocente (idBloco, idDocente) VALUES (?, ?)",
        (result[0], teacher_code),
    )
