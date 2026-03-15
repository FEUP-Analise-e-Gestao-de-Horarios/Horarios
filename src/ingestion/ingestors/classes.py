import sqlite3

from src.ingestion.schemas.classes import Degree, Subject
from src.ingestion.schemas.misc import Time, WeekDay


def ingest_degree(cursor: sqlite3.Cursor, degree: Degree) -> None:
    """Insert a degree record into the ``curso`` table.

    Args:
        cursor: Active SQLite cursor used to execute the INSERT statement.
        degree: Degree data to persist.
    """
    cursor.execute(
        "INSERT INTO curso(designacao, abreviacao) VALUES(?, ?)",
        (degree["name"], degree["acronym"]),
    )


def ingest_class(
    cursor: sqlite3.Cursor,
    degree_acronym: str,
    year_number: int,
    class_code: str,
) -> None:
    """Insert a class record into the ``turmas`` table.

    Args:
        cursor: Active SQLite cursor used to execute the INSERT statement.
        degree_acronym: Acronym of the degree the class belongs to.
        year_number: Academic year number within the degree.
        class_code: Unique identifier code of the class.
    """
    cursor.execute(
        "INSERT INTO turmas (idCurso, ano, codigo) VALUES (?, ?, ?)",
        (degree_acronym, year_number, class_code),
    )


def ingest_class_red_blocks(
    cursor: sqlite3.Cursor,
    class_code: str,
    time: Time,
    day: WeekDay,
) -> None:
    """Link an unavailability block to a class in the ``blocoTurma`` table.

    Looks up the ``blocosVermelhos`` row for the given time and day, then
    inserts a ``(block_id, class_code)`` pair into ``blocoTurma``,
    ignoring duplicates.

    Args:
        cursor: Active SQLite cursor used to execute the queries.
        class_code: Identifier of the class to associate with the block.
        time: Time slot encoded as ``HHMM`` (e.g. ``900`` for 09:00).
        day: Day of the week for the unavailability block.

    Raises:
        ValueError: If no matching row exists in ``blocosVermelhos`` for the
            given ``time`` and ``day``.
    """
    result = cursor.execute(
        """SELECT id FROM blocosVermelhos WHERE hora=? AND diaSemana=?""",
        (time, day),
    ).fetchone()

    if not result:
        raise ValueError(f"Red block not found for time={time}, day={day}")

    cursor.execute(
        "INSERT OR IGNORE INTO blocoTurma (idBloco, idTurma) VALUES (?, ?)",
        (result[0], class_code),
    )


def ingest_subject(
    cursor: sqlite3.Cursor,
    subject: Subject,
    degree_acronym: str,
) -> None:
    """Insert a subject record into the ``uc`` table, ignoring duplicates.

    Args:
        cursor: Active SQLite cursor used to execute the INSERT statement.
        subject: Subject data to persist.
        degree_acronym: Acronym of the degree the subject belongs to.
    """
    cursor.execute(
        "INSERT OR IGNORE INTO uc (codigo, idCurso, nome, sigla, codOcorrencia) VALUES (?, ?, ?, ?, ?)",
        (
            subject["code"],
            degree_acronym,
            subject["name"],
            subject["acronym"],
            subject["number"],
        ),
    )
