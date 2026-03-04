import sqlite3

from .models import Aula


def insert_aula(aula: Aula, cursor: sqlite3.Cursor) -> None:
    """
    Recebe um objeto Aula, extrai os seus dados e insere-os na base de dados.
    """

    isTeorica = aula.isTeorica
    duracao = aula.span
    salas = aula.salas
    turmas = aula.turmas
    docentes = aula.docentes
    hora = aula.hora
    dia = aula.dia
    semanaIni = aula.semanaIni
    semanaFin = aula.semanaFim
    codigo_uc = aula.cod_uc

    # Caso a aula não exista, são realizadas as inserções necessárias na DB
    stmtC = """INSERT INTO aula (horaInicial, duracao, diaSemana, teorico, semanaInicial, semanaFinal) VALUES (?, ?, ?, ?, ?, ?)"""
    cursor.execute(
        stmtC,
        (
            hora,
            duracao,
            dia,
            isTeorica,
            semanaIni,
            semanaFin,
        ),
    )
    id_aula = cursor.lastrowid

    stmtAUC = """INSERT OR IGNORE INTO aulaUC (idAula, idUC) VALUES (?, ?)"""
    cursor.execute(
        stmtAUC,
        (
            id_aula,
            codigo_uc,
        ),
    )

    for docente in docentes:
        stmtADC = (
            """INSERT OR IGNORE INTO aulaDocente (idAula, idDocente) VALUES (?, ?)"""
        )
        cursor.execute(
            stmtADC,
            (
                id_aula,
                docente,
            ),
        )

    for turma in turmas:
        stmtAT = """INSERT OR IGNORE INTO aulaTurmas (idAula, idTurma) VALUES (?, ?)"""
        cursor.execute(
            stmtAT,
            (
                id_aula,
                turma,
            ),
        )

        stmtTUC = """INSERT OR IGNORE INTO turmaUC (idTurma, idUC) VALUES (?, ?)"""
        cursor.execute(
            stmtTUC,
            (
                turma,
                codigo_uc,
            ),
        )

    for sala in salas.split(";"):
        stmtAS = """INSERT OR IGNORE INTO aulaSala (idAula, idSala) VALUES (?, ?)"""
        cursor.execute(
            stmtAS,
            (
                id_aula,
                sala,
            ),
        )
