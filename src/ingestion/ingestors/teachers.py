import sqlite3

from src.ingestion.schemas.misc import Time, WeekDay
from src.ingestion.schemas.teachers import TeacherPage


def ingest_teacher(cursor: sqlite3.Cursor, teacher: TeacherPage) -> None:
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
