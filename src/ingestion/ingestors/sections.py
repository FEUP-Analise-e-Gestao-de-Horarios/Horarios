import sqlite3
from datetime import date

from src.ingestion.schemas.misc import Time, WeekDay
from src.ingestion.schemas.sections import Course, Program, Session


def ingest_program(cursor: sqlite3.Cursor, program: Program) -> None:
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
