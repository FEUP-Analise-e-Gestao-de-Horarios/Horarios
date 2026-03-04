import re
from typing import Any

import requests
from bs4 import BeautifulSoup

from src.parser.utils import (
    get_dia_from_index,
    get_index,
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

    _DEFAULT_TIMEOUT: int = 30

    def _request(self, path: str) -> requests.Response:
        """Makes an internal HTTP GET request to base_url + path."""
        response = self._session.get(
            self.base_url + path, timeout=self._DEFAULT_TIMEOUT
        )
        response.raise_for_status()
        return response

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
        from collections import defaultdict

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
        from datetime import datetime

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
        from pathlib import Path

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
            with open(Path(__file__).parent.parent / "parser" / "Salas.txt") as file:
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
