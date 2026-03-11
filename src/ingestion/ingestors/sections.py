import sqlite3
from datetime import date

from src.ingestion.schemas.misc import Time, WeekDay
from src.ingestion.schemas.sections import Course, Program, Session


def ingest_program(cursor: sqlite3.Cursor, program: Program) -> None:
    """Insert a program record into the ``curso`` table.

    Args:
        cursor: Active SQLite cursor used to execute the INSERT statement.
        program: Program data to persist.
    """
    cursor.execute(
        "INSERT INTO curso(designacao, abreviacao) VALUES(?, ?)",
        (program["acronym"], program["name"]),
    )


def ingest_section(
    cursor: sqlite3.Cursor,
    program_acronym: str,
    year_number: int,
    section_code: str,
) -> None:
    """Insert a section record into the ``turmas`` table.

    Args:
        cursor: Active SQLite cursor used to execute the INSERT statement.
        program_acronym: Acronym of the program the section belongs to.
        year_number: Academic year number within the program.
        section_code: Unique identifier code of the section.
    """
    cursor.execute(
        "INSERT INTO turmas (idCurso, ano, codigo) VALUES (?, ?, ?)",
        (program_acronym, year_number, section_code),
    )


def ingest_section_red_blocks(
    cursor: sqlite3.Cursor,
    section_code: str,
    time: Time,
    day: WeekDay,
) -> None:
    """Link an unavailability block to a section in the ``blocoTurma`` table.

    Looks up the ``blocosVermelhos`` row for the given time and day, then
    inserts a ``(block_id, section_code)`` pair into ``blocoTurma``,
    ignoring duplicates.

    Args:
        cursor: Active SQLite cursor used to execute the queries.
        section_code: Identifier of the section to associate with the block.
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
        (result[0], section_code),
    )


def ingest_course(
    cursor: sqlite3.Cursor,
    course: Course,
    program_acronym: str,
) -> None:
    """Insert a course record into the ``uc`` table, ignoring duplicates.

    Args:
        cursor: Active SQLite cursor used to execute the INSERT statement.
        course: Course data to persist.
        program_acronym: Acronym of the program the course belongs to.
    """
    cursor.execute(
        "INSERT OR IGNORE INTO uc (codigo, idCurso, nome, sigla, codOcorrencia) VALUES (?, ?, ?, ?, ?)",
        (
            course["code"],
            program_acronym,
            course["name"],
            course["acronym"],
            course["number"],
        ),
    )


def ingest_session(
    cursor: sqlite3.Cursor,
    course_code: str,
    session: Session,
    start_date: date,
    end_date: date,
) -> None:
    """Insert a session and all its associations into the database.

    Inserts a row into ``aula``, then links it to its course (``aulaUC``),
    each teacher (``aulaDocente``), each section (``aulaTurmas``), and
    each room (``aulaSala``). Also records each (section, course) pair in
    ``turmaUC``. All inserts use ``INSERT OR IGNORE`` to avoid duplicates.

    Args:
        cursor: Active SQLite cursor used to execute the INSERT statements.
        course_code: Institutional code of the course this session belongs to.
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
        (id_aula, course_code),
    )

    for teacher in session["teachers"]:
        cursor.execute(
            "INSERT OR IGNORE INTO aulaDocente (idAula, idDocente) VALUES (?, ?)",
            (id_aula, teacher),
        )

    for section in session["sections"]:
        cursor.execute(
            "INSERT OR IGNORE INTO aulaTurmas (idAula, idTurma) VALUES (?, ?)",
            (id_aula, section),
        )
        cursor.execute(
            "INSERT OR IGNORE INTO turmaUC (idTurma, idUC) VALUES (?, ?)",
            (section, course_code),
        )

    for room in session["room"]:
        cursor.execute(
            "INSERT OR IGNORE INTO aulaSala (idAula, idSala) VALUES (?, ?)",
            (id_aula, room),
        )
