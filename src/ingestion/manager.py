import shutil
import sqlite3
from typing import Any

from src.core.models import Project
from src.parser.db import (
    insert_aula,
    insert_cursos,
    insert_turma,
    insert_ucs,
    pre_inserir_blocos_vermelhos,
)
from src.parser.models import Aula
from src.parser.utils import (
    are_weeks_overlapped,
    max_date,
    min_date,
)

from .scraper import Scraper


class IngestionManager:
    def __init__(self, project_url: str, path: str, proj_id: int, proj: Project):
        self.proj = proj
        self.proj_id = proj_id
        self.path = path
        self.turnosMap: dict[str, dict[int, list[str]]] = {}
        self.conn: sqlite3.Connection | None = None
        self.cursor: sqlite3.Cursor | None = None
        self.scraper: Scraper = Scraper(project_url)

    def run(self) -> None:
        """
        Função executora do parse.

        Cria a entrada do projeto na base de dados, a diretoria do projeto,
        e a ligação à base de dados. Chama as funções de parse para preencher
        a base de dados. No final, copia o conteúdo da general_database para
        a initial_database, e marca o projeto como parsed. Em caso de falha,
        a base de dados é eliminada e a diretoria é removida.
        """
        try:
            self._setup()

            docentes_menu, turmas_menu, salas_menu = self.scraper.get_menu()

            print("Project Started")
            pre_inserir_blocos_vermelhos(self.cursor, self.conn)

            self._parse_docentes(docentes_menu)
            self._parse_turmas(turmas_menu)
            self._parse_salas(salas_menu)
            self._parse_turnos()
            self._fix_turmas_without_turnos()
            self._cleanup_aulas()
            self._aulas_simultaneas()

            self._teardown_success()
            print("Project Parsed")

        except Exception:
            self._teardown_failure()
            raise

    # -----------------------------------------------------------------------
    # Setup / teardown
    # -----------------------------------------------------------------------

    def _setup(self) -> None:
        self.conn = sqlite3.connect(
            self.path + "/general_database.db", check_same_thread=False
        )
        self.cursor = self.conn.cursor()

    def _teardown_success(self) -> None:
        shutil.copy2(
            self.path + "/general_database.db", self.path + "/initial_database.db"
        )
        self.proj.isParsed = True
        self.proj.save()
        self.conn.close()
        self.scraper.close()

    def _teardown_failure(self) -> None:
        self.proj.delete()
        if self.conn is not None:
            self.conn.close()
        self.scraper.close()
        shutil.rmtree("./database/Project" + str(self.proj_id), ignore_errors=True)

    # -----------------------------------------------------------------------
    # Funções de parse
    # -----------------------------------------------------------------------

    def _parse_docentes(self, docentes_menu: Any) -> None:
        """
        Realiza o parse de todo o menu de docentes.

        Para cada docente, usa o Scraper para obter a informação do docente e os
        blocos vermelhos de cada página de horário. Insere os dados na base de dados.
        """
        for paths in self.scraper.get_docentes_links(docentes_menu):
            first_page = self.scraper.get_docente_page(paths[0])
            sigla = first_page["sigla"]
            nome = first_page["nome"]
            codigo = first_page["codigo"]

            self._insert_red_blocks_docente(first_page["red_blocks"], codigo)

            for path in paths[1:]:
                self._insert_red_blocks_docente(
                    self.scraper.get_red_blocks(path), codigo
                )

            stmt = """INSERT INTO docentes (numeroMecanografico, nome, abreviacao) VALUES (?, ?, ?)"""
            self.cursor.execute(stmt, (codigo, nome, sigla))
            self.conn.commit()

    def _insert_red_blocks_docente(
        self, red_blocks: list[tuple[int, str]], codigo: str
    ) -> None:
        """Translates (time, day) pairs to DB IDs and inserts into blocoDocente."""
        for time, day in red_blocks:
            stmt = """SELECT id FROM blocosVermelhos WHERE hora=? AND diaSemana=?"""
            result = self.cursor.execute(stmt, (time, day)).fetchone()
            if result:
                stmtT = """INSERT OR IGNORE INTO blocoDocente (idBloco, idDocente) VALUES (?, ?)"""
                self.cursor.execute(stmtT, (result[0], codigo))
        self.conn.commit()

    def _parse_turmas(self, turmas_menu: Any) -> None:
        """
        Realiza o parse do menu de turmas.

        Usa o Scraper para obter a estrutura de cursos, anos e turmas, visitando
        cada horário individual. Obtém todas as aulas de cada horário, inserindo
        a informação relevante na base de dados.
        """
        cursos = self.scraper.get_cursos(turmas_menu)
        insert_cursos(cursos, self.cursor)

        for curso_data in self.scraper.get_turmas_structure(turmas_menu):
            idCurso = curso_data["idCurso"]
            for ano_data in curso_data["anos"]:
                numeroStr = ano_data["numeroStr"]
                lista_de_aulas: set[Aula] = set()

                for turma_data in ano_data["turmas"]:
                    codigo = turma_data["codigo"]
                    links = turma_data["links"]

                    insert_turma(idCurso, numeroStr, codigo, self.cursor)
                    self.conn.commit()

                    parsed_vermelhos = False

                    for link in links:
                        schedule = self.scraper.get_turma_schedule(link)
                        insert_ucs(schedule["ucs"], idCurso, self.cursor)
                        self.conn.commit()

                        for aula_data in schedule["aulas"]:
                            sigla = aula_data["sigla"]
                            cod_uc = schedule["ucs"][sigla][0]

                            if aula_data["isTeorica"]:
                                self._update_turnos_map(cod_uc, aula_data["turmas"])

                            aula_obj = Aula({**aula_data, "cod_uc": cod_uc})
                            lista_de_aulas.add(aula_obj)

                        # Os blocos vermelhos de uma turma só precisam de ser
                        # parsed uma vez, já que não mudam entre semanas
                        if not parsed_vermelhos:
                            for time, day in schedule["red_blocks"]:
                                stmt = """SELECT id FROM blocosVermelhos WHERE hora=? AND diaSemana=?"""
                                result = self.cursor.execute(
                                    stmt, (time, day)
                                ).fetchone()
                                if result:
                                    stmtB = """INSERT OR IGNORE INTO blocoTurma (idBloco, idTurma) VALUES (?, ?)"""
                                    self.cursor.execute(stmtB, (result[0], codigo))
                            self.conn.commit()
                            parsed_vermelhos = True

                for aula in lista_de_aulas:
                    insert_aula(aula, self.cursor)

                lista_de_aulas = set()

        self.conn.commit()

    def _update_turnos_map(self, cod_uc: str, turnos: list[str]) -> None:
        """Adds or updates the turno entry for a teorica aula in the turnosMap."""
        if cod_uc in self.turnosMap:
            if turnos not in self.turnosMap[cod_uc].values():
                numeroTurno = max(self.turnosMap[cod_uc].keys())
                self.turnosMap[cod_uc][numeroTurno + 1] = turnos
                dicionario = self.turnosMap[cod_uc]
                chaves_ordenadas = sorted(
                    dicionario, key=lambda chave: dicionario[chave]
                )
                del self.turnosMap[cod_uc]
                self.turnosMap[cod_uc] = {}
                aux = 1
                for chave in chaves_ordenadas:
                    self.turnosMap[cod_uc][aux] = dicionario[chave]
                    aux += 1
        else:
            self.turnosMap[cod_uc] = {1: turnos}

    def _parse_salas(self, salas_menu: Any) -> None:
        """
        Realiza o parse das salas a partir do menu lateral.

        Usa o Scraper para obter a informação de cada sala e os blocos vermelhos
        de cada horário. Insere os dados relevantes na base de dados.
        """
        for sala_info in self.scraper.get_salas_info(salas_menu):
            sala = sala_info["sala"]
            stmt = """INSERT INTO salas(numero, tipo, capacidade, tamanhoComp) VALUES (?, ?, ?, ?)"""
            self.cursor.execute(
                stmt,
                (
                    sala,
                    sala_info["tipo"],
                    sala_info["capacidade"],
                    sala_info["tamanhoComp"],
                ),
            )
            self.conn.commit()

            for link in sala_info["links"]:
                for time, day in self.scraper.get_red_blocks(link):
                    stmtRB = """SELECT id FROM blocosVermelhos WHERE hora=? AND diaSemana=?"""
                    result = self.cursor.execute(stmtRB, (time, day)).fetchone()
                    if result:
                        stmtT = """INSERT OR IGNORE INTO salaBloco (idBloco, idSala) VALUES (?, ?)"""
                        self.cursor.execute(stmtT, (result[0], sala))
            self.conn.commit()

    def _parse_turnos(self) -> None:
        """
        Insere os turnos encontrados na base de dados.

        Usa a informação na estrutura turnosMap para preencher a tabela
        correspondente aos turnos na base de dados.
        """

        for uc in self.turnosMap:
            for number in self.turnosMap[uc]:
                for turno in self.turnosMap[uc][number]:
                    if isinstance(turno, list):
                        for turma in turno:
                            stmtS = """SELECT * FROM turno WHERE idTurma=? AND idUC=?"""
                            self.cursor.execute(stmtS, (turma, uc))
                            result = self.cursor.fetchall()
                            if len(result) == 0:
                                stmtT = """INSERT INTO turno (numero, idTurma, idUC) VALUES (?, ?, ?)"""
                                self.cursor.execute(stmtT, (number, turma, uc))
                                self.conn.commit()
                    else:
                        stmtS = """SELECT * FROM turno WHERE idTurma=? AND idUC=?"""
                        self.cursor.execute(stmtS, (turno, uc))
                        result = self.cursor.fetchall()
                        if len(result) == 0:
                            stmtT = """INSERT INTO turno (numero, idTurma, idUC) VALUES (?, ?, ?)"""
                            self.cursor.execute(stmtT, (number, turno, uc))
                            self.conn.commit()

    def _fix_turmas_without_turnos(self) -> None:
        """
        Atribui um turno às turmas que não têm um turno associado na base de dados.
        """

        query = """
            SELECT tu.idTurma, tu.idUC
            FROM turmaUC tu
            LEFT JOIN turno tn ON tu.idTurma = tn.idTurma
            WHERE tn.idTurma IS NULL
        """
        self.cursor.execute(query)
        missing_turmas = self.cursor.fetchall()

        for turma in missing_turmas:
            idTurma, idUC = turma
            query = """
                INSERT INTO turno (numero, idTurma, idUC)
                VALUES (0, ?, ?)
            """
            self.cursor.execute(query, (idTurma, idUC))
        self.conn.commit()

    def _cleanup_aulas(self) -> None:
        """
        Deduplica e funde aulas sobrepostas na base de dados.
        """
        stmtAulas = """SELECT DISTINCT diaSemana, horaInicial, duracao, teorico, idDocente, idUC, idTurma
                        FROM aula
                        JOIN aulaDocente ON aula.id = aulaDocente.idAula
                        JOIN aulaUC ON aula.id = aulaUC.idAula
                        JOIN aulaTurmas ON aula.id = aulaTurmas.idAula"""
        self.cursor.execute(stmtAulas)
        aulas = self.cursor.fetchall()

        for aula in aulas:
            dia, hora, duracao, isTeorica, docente, uc, turma = aula
            stmtTest = """SELECT * FROM aula
                          JOIN aulaDocente ON aula.id = aulaDocente.idAula
                          JOIN aulaUC ON aula.id = aulaUC.idAula
                          JOIN aulaTurmas ON aula.id = aulaTurmas.idAula
                          WHERE diaSemana=? AND horaInicial=? AND duracao=? AND teorico=? AND idDocente=? AND idUC=? AND idTurma=?"""
            self.cursor.execute(
                stmtTest, (dia, hora, duracao, isTeorica, docente, uc, turma)
            )
            results = self.cursor.fetchall()

            while len(results) > 1 and any(
                are_weeks_overlapped(
                    results[i][5], results[i][6], results[j][5], results[j][6]
                )
                for i in range(len(results))
                for j in range(i + 1, len(results))
            ):
                results.sort(key=lambda x: x[5])
                idAula1, si1, sf1 = results[0][0], results[0][5], results[0][6]
                idAula2, si2, sf2 = results[1][0], results[1][5], results[1][6]
                if are_weeks_overlapped(si1, sf1, si2, sf2):
                    ssi = min_date(si1, si2)
                    ssf = max_date(sf1, sf2)
                    results_list = list(results[0])
                    results_list[5] = ssi
                    results_list[6] = ssf
                    results[0] = tuple(results_list)
                    stmtUpdate = (
                        """UPDATE aula SET semanaInicial=?, semanaFinal=? WHERE id=?"""
                    )
                    self.cursor.execute(stmtUpdate, (ssi, ssf, idAula1))
                    for table in ["aulaDocente", "aulaUC", "aulaSala", "aulaTurmas"]:
                        self.cursor.execute(
                            f"DELETE FROM {table} WHERE idAula=?", (idAula2,)
                        )
                    self.cursor.execute("DELETE FROM aula WHERE id=?", (idAula2,))
                    results.pop(1)
                    continue
                results.pop(0)
        self.conn.commit()

    def _aulas_simultaneas(self) -> None:
        """
        Encontra aulas simultâneas no horário e insere a informação na base de dados.

        Realiza uma query à base de dados para encontrar aulas simultâneas de
        cursos diferentes. Aulas simultâneas têm os mesmos: docente, sala, dia, e
        hora. Há também uma sobreposição nas semanas em que ocorrem. No entanto,
        o curso e a UC têm de ser diferentes. Depois de encontradas as aulas, são
        inseridas numa tabela apropriada na base de dados.
        """

        query = """
            SELECT DISTINCT
                CASE WHEN a1.id < a2.id THEN a1.id ELSE a2.id END AS id_aula1,
                CASE WHEN a1.id < a2.id THEN a2.id ELSE a1.id END AS id_aula2,
                uc1.idCurso AS id_curso1,
                uc2.idCurso AS id_curso2
            FROM aula AS a1
            JOIN aulaSala AS asala1 ON a1.id = asala1.idAula
            JOIN aulaDocente AS ad1 ON a1.id = ad1.idAula
            JOIN aulaUC AS auc1 ON a1.id = auc1.idAula
            JOIN uc AS uc1 ON auc1.idUC = uc1.codigo
            JOIN aula AS a2
            JOIN aulaSala AS asala2 ON a2.id = asala2.idAula
            JOIN aulaDocente AS ad2 ON a2.id = ad2.idAula
            JOIN aulaUC AS auc2 ON a2.id = auc2.idAula
            JOIN uc AS uc2 ON auc2.idUC = uc2.codigo
            WHERE a2.id > a1.id
                AND ad1.idDocente = ad2.idDocente
                AND asala1.idSala = asala2.idSala
                AND a1.diaSemana = a2.diaSemana
                AND a1.horaInicial = a2.horaInicial
                AND (
                    (a1.semanaInicial <= a2.semanaFinal AND a1.semanaFinal >= a2.semanaInicial)
                    OR
                    (a1.semanaInicial >= a2.semanaInicial AND a1.semanaFinal <= a2.semanaFinal)
                    OR
                    (a1.semanaInicial <= a2.semanaInicial AND a1.semanaFinal >= a2.semanaFinal)
                )
                AND uc1.idCurso <> uc2.idCurso;
        """
        self.cursor.execute(query)
        aulas_sim = self.cursor.fetchall()

        for entry in aulas_sim:
            idAula1, idAula2, idCurso1, idCurso2 = entry
            query = """
                INSERT into aulasSimultaneas (aula1, aula2, curso1, curso2)
                VALUES (?, ?, ?, ?)
            """
            self.cursor.execute(query, (idAula1, idAula2, idCurso1, idCurso2))

        self.conn.commit()
