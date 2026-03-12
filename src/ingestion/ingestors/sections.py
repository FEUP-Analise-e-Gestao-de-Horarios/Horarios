import sqlite3
from datetime import date

from src.ingestion.schemas.misc import Time, WeekDay
from src.ingestion.schemas.sections import Degree, Session, Subject


def ingest_degree(cursor: sqlite3.Cursor, degree: Degree) -> None:
    """Insert a degree record into the ``curso`` table.

    Args:
        cursor: Active SQLite cursor used to execute the INSERT statement.
        degree: Degree data to persist.
    """
    cursor.execute(
        "INSERT INTO curso(designacao, abreviacao) VALUES(?, ?)",
        (degree["acronym"], degree["name"]),
    )


def ingest_group(
    cursor: sqlite3.Cursor,
    degree_acronym: str,
    year_number: int,
    group_code: str,
) -> None:
    """Insert a group record into the ``turmas`` table.

    Args:
        cursor: Active SQLite cursor used to execute the INSERT statement.
        degree_acronym: Acronym of the degree the group belongs to.
        year_number: Academic year number within the degree.
        group_code: Unique identifier code of the group.
    """
    cursor.execute(
        "INSERT INTO turmas (idCurso, ano, codigo) VALUES (?, ?, ?)",
        (degree_acronym, year_number, group_code),
    )


def ingest_group_red_blocks(
    cursor: sqlite3.Cursor,
    group_code: str,
    time: Time,
    day: WeekDay,
) -> None:
    """Link an unavailability block to a group in the ``blocoTurma`` table.

    Looks up the ``blocosVermelhos`` row for the given time and day, then
    inserts a ``(block_id, group_code)`` pair into ``blocoTurma``,
    ignoring duplicates.

    Args:
        cursor: Active SQLite cursor used to execute the queries.
        group_code: Identifier of the group to associate with the block.
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
        (result[0], group_code),
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


def ingest_session(
    cursor: sqlite3.Cursor,
    subject_code: str,
    session: Session,
    start_date: date,
    end_date: date,
) -> None:
    """Insert a session and all its associations into the database.

    Inserts a row into ``aula``, then links it to its subject (``aulaUC``),
    each teacher (``aulaDocente``), each group (``aulaTurmas``), and
    each room (``aulaSala``). Also records each (group, subject) pair in
    ``turmaUC``. All inserts use ``INSERT OR IGNORE`` to avoid duplicates.

    Args:
        cursor: Active SQLite cursor used to execute the INSERT statements.
        subject_code: Institutional code of the subject this session belongs to.
        session: Session data to persist.
        start_date: First day of the week range covered by this session.
        end_date: Last day of the week range covered by this session.
    """
    cursor.execute(
        "INSERT INTO aula (horaInicial, duracao, diaSemana, teorico, semanaInicial, semanaFinal) VALUES (?, ?, ?, ?, ?, ?)",
        (
            session["start_time"],
            session["duration"],
            session["weekday"],
            session["is_theoretical"],
            start_date,
            end_date,
        ),
    )

    id_aula = cursor.lastrowid
    cursor.execute(
        "INSERT OR IGNORE INTO aulaUC (idAula, idUC) VALUES (?, ?)",
        (id_aula, subject_code),
    )

    for teacher in session["teachers"]:
        cursor.execute(
            "INSERT OR IGNORE INTO aulaDocente (idAula, idDocente) VALUES (?, ?)",
            (id_aula, teacher),
        )

    for group in session["groups"]:
        cursor.execute(
            "INSERT OR IGNORE INTO aulaTurmas (idAula, idTurma) VALUES (?, ?)",
            (id_aula, group),
        )
        cursor.execute(
            "INSERT OR IGNORE INTO turmaUC (idTurma, idUC) VALUES (?, ?)",
            (group, subject_code),
        )

    for room in session["room"]:
        cursor.execute(
            "INSERT OR IGNORE INTO aulaSala (idAula, idSala) VALUES (?, ?)",
            (id_aula, room),
        )
