import sqlite3
from datetime import date

from src.ingestion.schemas.classes import Degree, Session, Subject
from src.ingestion.schemas.misc import Time, WeekDay


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


def ingest_classred_blocks(
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


def ingest_session(
    cursor: sqlite3.Cursor,
    subject_code: str,
    session: Session,
    start_date: date,
    end_date: date,
) -> None:
    """Insert a session and all its associations into the database.

    Inserts a row into ``aula``, then links it to its subject (``aulaUC``),
    each teacher (``aulaDocente``), each class (``aulaTurmas``), and
    each room (``aulaSala``). Also records each (class, subject) pair in
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

    for class_ in session["classes"]:
        cursor.execute(
            "INSERT OR IGNORE INTO aulaTurmas (idAula, idTurma) VALUES (?, ?)",
            (id_aula, class_),
        )
        cursor.execute(
            "INSERT OR IGNORE INTO turmaUC (idTurma, idUC) VALUES (?, ?)",
            (class_, subject_code),
        )

    for room in session["room"]:
        cursor.execute(
            "INSERT OR IGNORE INTO aulaSala (idAula, idSala) VALUES (?, ?)",
            (id_aula, room),
        )
