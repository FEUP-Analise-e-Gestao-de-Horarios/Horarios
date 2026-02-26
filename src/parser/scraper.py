import re
import shutil
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

from src.core.models import Project

from .db import (
    insert_aula,
    insert_cursos,
    insert_turma,
    insert_ucs,
    pre_inserir_blocos_vermelhos,
)
from .directories import createDir
from .models import Aula
from .utils import (
    are_weeks_overlapped,
    get_dia_from_index,
    get_index,
    max_date,
    min_date,
    table_to_matrix,
)

# Algumas tipologias encontradas
# 14 - O, 15 - OT, 16 - Pratica, 17 - PL, 18 - S
# 19 - Teorica, 20 - TC, 21 - Teorico-Pratica
# Não existe tipologia para além da 21
tipologias = ["td_tipologia_" + str(id) for id in range(1, 22)]


class Scraper:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self._session: requests.Session = requests.Session()

    # -------------------------------------------------------------------
    # Internal request helper
    # -------------------------------------------------------------------

    def _request(self, path: str) -> requests.Response:
        """Makes an internal HTTP GET request to base_url + path."""
        return self._session.get(self.base_url + path)

    # -------------------------------------------------------------------
    # Internal HTML extraction helpers
    # -------------------------------------------------------------------

    def _extract_red_blocks(self, soup: BeautifulSoup) -> list[tuple[int, str]]:
        """Extracts (time, day) pairs for red blocks from a parsed schedule page."""
        vermelhos = soup.find_all("td", {"class": "td_vermelha"})
        if not vermelhos:
            return []

        table = soup.find("center").find("table", {"class": "tabela_principal"})
        matrix = table_to_matrix(table)

        days = vermelhos[0].parent.parent.findChildren(recursive=False)[3]
        daySpans: dict[str, Any] = {}
        for i, day in enumerate(days.findChildren()):
            if i == 0:
                continue
            daySpans[day.text] = day.get("colspan")

        result = []
        for item in vermelhos:
            parent = item.parent
            index, matrix = get_index(item, matrix)
            time = int(parent.findChild().text.replace(":", ""))
            day = get_dia_from_index(index, daySpans)
            result.append((time, day))

        return result

    def _extract_ucs(self, soup: BeautifulSoup) -> dict[str, list]:
        """Extracts UC data from a parsed turma schedule page."""
        table = [str(row) for row in soup.findAll("table")[4].findAll("tr")[2:]]
        ucs = {}
        for row in table:
            row_items = row.split('<td align="left" valign="middle">')[1:]
            (codigo_nome, sigla, numero_uc) = (
                item.split("</td>")[0] for item in row_items
            )
            (codigo, nome) = codigo_nome.split(" - ", 1)
            ucs[sigla] = [codigo, nome, numero_uc]
        return ucs

    def _extract_aulas(
        self, soup: BeautifulSoup, semanaIni: str, semanaFim: str
    ) -> list[dict[str, Any]]:
        """Extracts raw aula data from a parsed schedule page."""
        aulaBlocks = soup.find("center").find_all("td", {"class": tipologias})
        if not aulaBlocks:
            return []

        # Build docente abbreviation → code list mapping
        docentes_table = soup.findAll("table")[3].findAll("tr")[2:]
        docentes_table = list(map(str, docentes_table))
        docentes_temp: defaultdict[str, list[str]] = defaultdict(list)
        for item in docentes_table:
            parts = item.split('<td align="left" valign="middle">')
            abrevs = parts[2].split("</td>")[0]
            codes = parts[3].split("</td>")[0]
            docentes_temp[abrevs].append(codes)

        # Build day-span mapping
        dias = aulaBlocks[0].parent.parent.findChildren(recursive=False)[3]
        diaSpans: dict[str, Any] = {}
        for i, dia in enumerate(dias.findChildren()):
            if i == 0:
                continue
            diaSpans[dia.text] = dia.get("colspan")

        table = soup.find("center").find("table", {"class": "tabela_principal"})
        matrix = table_to_matrix(table)

        aulas = []
        for aulaBlock in aulaBlocks:
            count = 0
            aula: dict[str, Any] = {}
            aula["isTeorica"] = aulaBlock.get("class")[0] == "td_tipologia_19"
            aula["span"] = aulaBlock.get("rowspan")
            pattern = r"\[(.*?)\]"
            matches = re.findall(pattern, aulaBlock.text)
            aula["salas"] = matches[2] if len(matches) > 2 else "Online"
            aula["turmas"] = matches[0].split("; ")

            docentes_aulaBlock = (
                matches[1].replace("(", "").replace(")", "").split("; ")
            )

            aula["semanaIni"] = semanaIni
            aula["semanaFim"] = semanaFim

            lista_docentes = []
            for i in docentes_aulaBlock:
                if len(docentes_temp[i]) == 1:
                    lista_docentes.append(docentes_temp[i][0])
                else:
                    lista_docentes.append(docentes_temp[i][count])
                    count += 1
            aula["docentes"] = lista_docentes

            aula["sigla"] = aulaBlock.contents[0]
            pai = aulaBlock.parent
            aula["hora"] = int(pai.findChild().text.replace(":", ""))
            index, matrix = get_index(aulaBlock, matrix)
            aula["dia"] = get_dia_from_index(index, diaSpans)
            aulas.append(aula)

        return aulas

    # -------------------------------------------------------------------
    # Public page-navigation methods
    # -------------------------------------------------------------------

    def get_menu(self) -> tuple[Any, Any, Any]:
        """
        Fetches the main page and navigation menu.

        Returns a tuple of (docentes_menu, turmas_menu, salas_menu) BeautifulSoup
        submenu elements that can be passed to the other Scraper methods.
        """
        response = self._session.get(self.base_url)
        soup = BeautifulSoup(response.content, "html.parser")
        links = soup.find("frame", {"name": "links"})
        src = links["src"]
        menu_soup = BeautifulSoup(self._request(src).content, "html.parser")
        menu = menu_soup.find("ul", {"id": "menu"})
        children = menu.findChildren(recursive=False)
        return children[0], children[1], children[2]

    def get_docentes_links(self, docentes_menu: Any) -> list[list[str]]:
        """
        Extracts groups of schedule page paths for each docente from the menu.

        Returns a list of path groups — one list per docente, where each element
        is a relative URL path for a schedule page belonging to that docente.
        """
        children = docentes_menu.find("ul").findChildren(recursive=False)
        result = []
        for child in children:
            content = child.find("ul").find_all("li", recursive=False)
            paths = [i.find("a", recursive=False)["href"] for i in content]
            result.append(paths)
        return result

    def get_docente_page(self, path: str) -> dict[str, Any]:
        """
        Extracts docente info and red blocks from a schedule page.

        Returns a dict with keys: sigla, nome, codigo, red_blocks.
        red_blocks is a list of (time, day) tuples.
        """
        response = self._request(path)
        soup = BeautifulSoup(response.content, "html.parser")
        content = soup.find("td", {"class": "cabtitulo"}).contents
        content = str(content)
        if '"' in content:
            first = content.split('"')[1]
            sigla = content.split("<br/>, '")[1].split("'")[0]
            nome = first[len(sigla) :] if sigla in first else ""
            codigo = content.split("<br/>, '")[2].split("'")[0]
        else:
            content = content.split("', <br/>, '")
            sigla = content[1].split("'")[0]
            nome = content[0][len(sigla) + 2 :] if sigla in content[0] else ""
            codigo = content[2].split("'")[0]
        if " - " in nome:
            nome = nome[3:]
        if nome == "":
            nome = sigla
        nome = re.sub(r"[^\w\s]", "", nome)
        return {
            "sigla": sigla,
            "nome": nome,
            "codigo": codigo,
            "red_blocks": self._extract_red_blocks(soup),
        }

    def get_red_blocks(self, path: str) -> list[tuple[int, str]]:
        """
        Extracts red block (time, day) pairs from a schedule page.
        """
        response = self._request(path)
        soup = BeautifulSoup(response.content, "html.parser")
        return self._extract_red_blocks(soup)

    def get_cursos(self, turmas_menu: Any) -> set[tuple[str, str]]:
        """
        Extracts (nome, abreviatura) course pairs from the turmas menu.
        """
        children = turmas_menu.find("ul").findChildren(recursive=False)
        allCursos: set[tuple[str, str]] = set()
        for curso in children:
            info = curso.find("a").contents
            abreviatura = info[0].split(" - ")[0]
            nome = info[0].split(" - ", 1)[1]
            allCursos.add((nome, abreviatura))
        return allCursos

    def get_turmas_structure(self, turmas_menu: Any) -> list[dict[str, Any]]:
        """
        Extracts the hierarchical structure of courses, years, and turmas.

        Returns a list of dicts, each with keys:
          idCurso, anos — where anos is a list of dicts with keys:
            numeroStr, turmas — where turmas is a list of dicts with keys:
              codigo, links (list of relative URL paths for each schedule week).
        """
        children = turmas_menu.find("ul").findChildren(recursive=False)
        result = []
        for child in children:
            idCurso = child.find("a").contents[0].split(" - ")[0]
            anos_items = child.find("ul").findChildren(recursive=False)
            anos = []
            for ano in anos_items:
                numeroStr = ano.find("a").contents[0].split(" ")[1]
                plano_turmas = ano.find("ul").find("li")
                turmas_list = plano_turmas.find("ul").findChildren(recursive=False)
                turmas = []
                for turma in turmas_list:
                    codigo = str(turma.find("a").contents).split("'")[1]
                    semanasLi = turma.find("ul").find_all("li")
                    links = [
                        semana.find("a", recursive=False)["href"]
                        for semana in semanasLi
                    ]
                    turmas.append({"codigo": codigo, "links": links})
                anos.append({"numeroStr": numeroStr, "turmas": turmas})
            result.append({"idCurso": idCurso, "anos": anos})
        return result

    def get_turma_schedule(self, path: str) -> dict[str, Any]:
        """
        Extracts all data from a turma schedule page.

        Returns a dict with keys: semanaIni, semanaFim, ucs, aulas, red_blocks.
        ucs maps UC sigla to [codigo, nome, numero_uc].
        aulas is a list of raw aula dicts (sigla, isTeorica, turmas, docentes,
        salas, hora, dia, semanaIni, semanaFim).
        red_blocks is a list of (time, day) tuples.
        """
        response = self._request(path)
        soup = BeautifulSoup(response.content, "html.parser")

        semanas = soup.find("td", {"class": "cabtitulo"}).contents
        semanas = str(semanas[-1])
        semanaIniEFim = semanas.split("Semanas: ")[1]
        semanaIni, _, semanaFim = semanaIniEFim.partition(" - ")
        if not semanaFim:
            semanaFim = semanaIni

        si_obj = datetime.strptime(semanaIni, "%d/%m/%Y")
        sf_obj = datetime.strptime(semanaFim, "%d/%m/%Y")
        semanaIni = si_obj.strftime("%Y-%m-%d")
        semanaFim = sf_obj.strftime("%Y-%m-%d")

        return {
            "semanaIni": semanaIni,
            "semanaFim": semanaFim,
            "ucs": self._extract_ucs(soup),
            "aulas": self._extract_aulas(soup, semanaIni, semanaFim),
            "red_blocks": self._extract_red_blocks(soup),
        }

    def get_salas_info(self, salas_menu: Any) -> list[dict[str, Any]]:
        """
        Extracts sala information from the salas menu.

        Returns a list of dicts with keys: sala, tipo, capacidade, tamanhoComp,
        and links (list of relative URL paths for sala schedule pages).
        """
        children = salas_menu.find("ul").findChildren(recursive=False)
        result = []
        for child in children:
            a_list = child.find_all("a", {"class": "timetable-link"})
            content = child.find("a").contents
            if "__cf_email__" in str(content):
                content = ["EaD"]
            sala = str(content).split("'")[1]

            tipo = "Desconhecido"
            capacidade = "Desconhecido"
            tamanhoComp = "Desconhecido"
            with open(Path(__file__).parent / "Salas.txt") as file:
                for line in file:
                    if sala in line:
                        tipo = line.strip().split(" - ")[0]
                        capacidade = line.strip().split(" - ")[-1]
                        if tipo == "Anf":
                            if "." in capacidade:
                                capacidade = capacidade[-2:]
                            tamanhoComp = "N/A"
                        elif tipo == "PCs":
                            if capacidade == "Grandes":
                                tamanhoComp = "> 21"
                            elif capacidade == "Media20":
                                capacidade = "Media"
                                tamanhoComp = "20"
                            elif capacidade == "Media16":
                                capacidade = "Media"
                                tamanhoComp = "16"
                            else:
                                tamanhoComp = "< 15"
                        else:
                            tamanhoComp = "N/A"
                        break

            links = [a.get("href") for a in a_list]
            result.append(
                {
                    "sala": sala,
                    "tipo": tipo,
                    "capacidade": capacidade,
                    "tamanhoComp": tamanhoComp,
                    "links": links,
                }
            )
        return result

    def close(self) -> None:
        """Closes the HTTP session."""
        self._session.close()


class Parser:
    def __init__(self, paginas: str, user_pk: str, name: str):
        self.user_pk = user_pk
        self.name = name
        self.turnosMap: dict[str, dict[int, list[str]]] = {}
        self.conn: sqlite3.Connection | None = None
        self.cursor: sqlite3.Cursor | None = None
        self.proj = None
        self.proj_id: int | None = None
        self.path: str | None = None
        self.scraper: Scraper = Scraper(paginas)

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
        self.path, self.proj_id = createDir(self.user_pk, self.name)
        assert self.path is not None
        self.proj = Project.objects.get(project=self.name)
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
        if self.proj is not None:
            self.proj.delete()
        if self.conn is not None:
            self.conn.close()
        if self.proj_id is not None:
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
                (sala, sala_info["tipo"], sala_info["capacidade"], sala_info["tamanhoComp"]),
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
