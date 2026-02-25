import sqlite3

from .models import Aula


def pre_inserir_blocos_vermelhos(
    cursor: sqlite3.Cursor, conn: sqlite3.Connection
) -> None:
    """
    Preenche a tabela dos blocos vermelhos no arranque do parse.

    A tabela de blocos vermelhos, usada para consulta na base de dados,
    é preenchida com todos os possíveis blocos de indisponibilidade que
    podem ser encontrados nos restantes horários.
    """

    # Verificar se a tabela já está preenchida
    stmt_count = """SELECT COUNT(*) FROM blocosVermelhos"""
    cursor.execute(stmt_count)
    count = cursor.fetchone()[0]

    # Se a tabela estiver vazia, então preenche
    if count == 0:
        for dia in ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]:
            for hora in range(
                800, 2201, 100
            ):  # Horários de 8h às 22h em intervalos de 100 minutos
                for minuto in [0, 30]:  # Minutos 0 e 30
                    horario = hora + minuto
                    stmt = """INSERT INTO blocosVermelhos (hora, diaSemana) VALUES (?, ?)"""
                    cursor.execute(stmt, (horario, dia))
                    conn.commit()


def insert_cursos(cursos: list[tuple[str, str]], cursor: sqlite3.Cursor) -> None:
    """
    Recebe a lista dos cursos e insere-os na base de dados.
    """

    for nome, abreviatura in cursos:
        stmt = """INSERT INTO curso(designacao, abreviacao) VALUES(?, ?)"""
        cursor.execute(stmt, (nome, abreviatura))


def insert_ucs(
    ucs: dict[str, list[str, str, str]], id_curso: str, cursor: sqlite3.Cursor
) -> None:
    """
    Recebe a lista das UCs e insere-as na base de dados
    """

    for sigla, (codigo, nome, numero) in ucs.items():
        stmt = """INSERT OR IGNORE INTO uc (codigo, idCurso, nome, sigla, codOcorrencia) VALUES (?, ?, ?, ?, ?)"""
        cursor.execute(stmt, (codigo, id_curso, nome, sigla, numero))


def insert_turma(
    id_curso: str, ano: str, codigo_turma: str, cursor: sqlite3.Cursor
) -> None:
    """
    Recebe dados sobre uma turma e insere a informação na base de dados.
    """

    stmt = """INSERT INTO turmas (idCurso, ano, codigo) VALUES (?, ?, ?)"""
    cursor.execute(stmt, (id_curso, ano, codigo_turma))


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
