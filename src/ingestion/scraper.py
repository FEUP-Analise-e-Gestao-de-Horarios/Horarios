import re
from datetime import datetime
from typing import Any, cast

import requests
from bs4 import BeautifulSoup, Tag

from src.ingestion.schemas import (
    ClassPages,
    CourseInfo,
    RedBlock,
    TeacherPage,
    YearInfo,
)
from src.ingestion.utils import get_cell_column, matrix_from_html_table
from src.parser.utils import get_dia_from_index

# Algumas tipologias encontradas
# 14 - O, 15 - OT, 16 - Pratica, 17 - PL, 18 - S
# 19 - Teorica, 20 - TC, 21 - Teorico-Pratica
# Não existe tipologia para além da 21
tipologias = ["td_tipologia_" + str(id) for id in range(1, 22)]


class Scraper:
    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self._session = requests.Session()

    # -------------------------------------------------------------------
    # Internal request helper
    # -------------------------------------------------------------------

    _DEFAULT_TIMEOUT: int = 30

    def _request(self, path: str) -> BeautifulSoup:
        """Makes an internal HTTP GET request to base_url + path."""
        response = self._session.get(
            self.base_url + path,
            timeout=self._DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")

    # -------------------------------------------------------------------
    # Internal HTML extraction helpers
    # -------------------------------------------------------------------

    @staticmethod
    def _extract_teacher_links(docentes_menu: Tag) -> list[str]:
        """Extract all teacher schedule page URLs from the docentes menu.

        Navigates the two-level nested ``<ul>`` structure of the menu,
        collecting the ``href`` of every teacher link.

        Args:
            docentes_menu: The ``<li>`` tag for the "Docentes" menu entry.

        Returns:
            A list of relative URL paths, one per teacher.

        Raises:
            ValueError: If expected structural elements are missing from the menu.
        """
        ul = docentes_menu.find("ul")
        if ul is None:
            raise ValueError("Could not find <ul> in docentes menu")

        children = ul.find_all(recursive=False)
        result: list[str] = []

        for child in children:
            inner_ul = child.find("ul")
            if inner_ul is None:
                raise ValueError("Could not find <ul> in child menu item")

            content = inner_ul.find_all("li", recursive=False)
            for i in content:
                a = i.find("a", recursive=False)
                if a is None:
                    raise ValueError("Could not find <a> in <li>")

                href = a["href"]
                if not isinstance(href, str):
                    raise ValueError(f"Expected href to be a str, got {type(href)}")

                result.append(href)

        return result

    @staticmethod
    def _extract_classes_links(turmas_menu: Tag) -> list[CourseInfo]:
        ul = turmas_menu.find("ul")
        if ul is None:
            raise ValueError("Could not find <ul> in turmas menu")

        result: list[CourseInfo] = []
        for child in ul.find_all(recursive=False):
            child_a = child.find("a")
            if child_a is None:
                raise ValueError("Could not find <a> in turmas menu child")

            course_info = child_a.contents
            if not course_info:
                raise ValueError("Empty <a> contents in curso menu item")

            course_id, course_name = str(course_info[0]).split(" - ")

            child_ul = child.find("ul")
            if child_ul is None:
                raise ValueError(f"Could not find <ul> for curso '{course_id}'")

            years: list[YearInfo] = []
            for year in child_ul.find_all(recursive=False):
                year_a = year.find("a")
                if year_a is None:
                    raise ValueError(
                        f"Could not find <a> in ano item for curso '{course_id}'"
                    )

                year_number = int(str(year_a.contents[0]).split(" ")[1])

                plan_ul = year.find("ul")
                if plan_ul is None:
                    raise ValueError(
                        f"Could not find plano <ul> for ano '{year_number}'"
                    )

                plan_li = plan_ul.find("li")
                if plan_li is None:
                    raise ValueError(
                        f"Could not find <li> in plano for ano '{year_number}'"
                    )

                class_ul = plan_li.find("ul")
                if class_ul is None:
                    raise ValueError(
                        f"Could not find turmas <ul> for ano '{year_number}'"
                    )

                classes: list[ClassPages] = []
                for class_ in class_ul.find_all(recursive=False):
                    class_a = class_.find("a")
                    if class_a is None:
                        raise ValueError(
                            f"Could not find <a> in turma item for ano '{year_number}'"
                        )

                    class_code = str(class_a.contents[0])

                    weeks_ul = class_.find("ul")
                    if weeks_ul is None:
                        raise ValueError(
                            f"Could not find semanas <ul> for turma '{class_code}'"
                        )

                    links: list[str] = []
                    for week in weeks_ul.find_all("li"):
                        week_a = week.find("a", recursive=False)
                        if week_a is None:
                            raise ValueError(
                                f"Could not find <a> in semana item for turma '{class_code}'"
                            )

                        week_href = week_a["href"]
                        if not isinstance(week_href, str):
                            raise ValueError(
                                f"Expected href to be str, got {type(week_href)}"
                            )

                        links.append(week_href)
                    classes.append({"code": class_code, "links": links})
                years.append({"number": year_number, "classes": classes})
            result.append(
                {"abbreviation": course_id, "name": course_name, "years": years}
            )
        return result

    @staticmethod
    def _extract_red_blocks(soup: BeautifulSoup) -> list[RedBlock]:
        """Extract unavailable time slots from a schedule page.

        Red blocks (``td_vermelha``) represent time slots where a teacher or
        room is unavailable. The method reads the day-span header to map column
        positions to weekday names, then builds a matrix of the main schedule
        table to locate each red cell's column and derive its weekday.

        Args:
            soup: Parsed HTML of a schedule page.

        Returns:
            A list of ``(time, day)`` tuples, e.g. ``(900, "Segunda")``,
            one entry per red block. Returns an empty list if none are found.

        Raises:
            ValueError: If expected structural elements are missing from the page.
        """
        # -- Build week day <-> table width dict--------------------------------
        red_cells = soup.find_all("td", {"class": "td_vermelha"})
        if not red_cells:
            return []

        row = red_cells[0].parent
        if row is None:
            raise ValueError("Red block <td> has no parent row")

        header_row = row.parent
        if header_row is None:
            raise ValueError("Red block row has no parent")

        header_children = header_row.find_all(recursive=False)
        if len(header_children) < 4:
            raise ValueError(
                f"Expected at least 4 children in header row, got {len(header_children)}"
            )

        days = header_children[3]
        daySpans: dict[str, int] = {}
        for i, day in enumerate(days.findChildren()):
            if i == 0:
                continue
            daySpans[day.text] = int(str(day.get("colspan") or 1))

        # -- Build table matrix ------------------------------------------------
        center = soup.find("center")
        if center is None:
            raise ValueError("Could not find <center> in schedule page")

        table = center.find("table", {"class": "tabela_principal"})
        if table is None:
            raise ValueError("Could not find <table class='tabela_principal'>")

        matrix = matrix_from_html_table(table)
        result: list[RedBlock] = []

        for item in red_cells:
            table_row = item.parent
            if table_row is None:
                raise ValueError("Red block <td> has no parent")

            index = get_cell_column(item, matrix)
            first_child = table_row.find()
            if first_child is None:
                raise ValueError("Red block row has no children")

            time = int(first_child.text.replace(":", ""))
            day = get_dia_from_index(index, daySpans)
            result.append((time, day))

        return result

    def _extract_aulas(
        self, soup: BeautifulSoup, semanaIni: datetime, semanaFim: datetime
    ) -> list[dict[str, Any]]:
        """Extracts raw aula data from a parsed schedule page."""
        from collections import defaultdict

        aulaBlocks = soup.find("center").find_all("td", {"class": tipologias})
        if not aulaBlocks:
            return []

        # Build teacher abbreviation → code list mapping
        teachers_table = cast(Tag, soup.findAll("table")[3])
        teachers_rows: list[str] = list(map(str, teachers_table.find_all("tr")[2:]))
        teachers_temp: defaultdict[str, list[str]] = defaultdict(list)
        for item in teachers_rows:
            parts = item.split('<td align="left" valign="middle">')
            abrevs = parts[2].split("</td>")[0]
            codes = parts[3].split("</td>")[0]
            teachers_temp[abrevs].append(codes)

        # Build day-span mapping
        dias = aulaBlocks[0].parent.parent.findChildren(recursive=False)[3]
        diaSpans: dict[str, Any] = {}
        for i, dia in enumerate(dias.findChildren()):
            if i == 0:
                continue
            diaSpans[dia.text] = dia.get("colspan")

        table = soup.find("center").find("table", {"class": "tabela_principal"})
        matrix = matrix_from_html_table(table)

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

            aula_teachers = matches[1].replace("(", "").replace(")", "").split("; ")

            aula["semanaIni"] = semanaIni
            aula["semanaFim"] = semanaFim

            teachers = []
            for i in aula_teachers:
                if len(teachers_temp[i]) == 1:
                    teachers.append(teachers_temp[i][0])
                else:
                    teachers.append(teachers_temp[i][count])
                    count += 1
            aula["docentes"] = teachers

            aula["sigla"] = aulaBlock.contents[0]
            pai = aulaBlock.parent
            aula["hora"] = int(pai.findChild().text.replace(":", ""))
            index, matrix = get_cell_column(aulaBlock, matrix)
            aula["dia"] = get_dia_from_index(index, diaSpans)
            aulas.append(aula)

        return aulas

    # -------------------------------------------------------------------
    # Public page-navigation methods
    # -------------------------------------------------------------------

    def read_menu(self) -> tuple[list[str], list[CourseInfo], Tag]:
        soup = self._request("")

        links = soup.find("frame", {"name": "links"})
        if links is None:
            raise ValueError("Could not find frame with name 'links'")

        src = links["src"]
        if not isinstance(src, str):
            raise ValueError(f"Expected 'src' to be a str, got {type(src)}")

        menu_soup = self._request(src)

        menu = menu_soup.find("ul", {"id": "menu"})
        if menu is None:
            raise ValueError("Could not find ul with id 'menu'")

        def find_li(label: str):
            for c in menu.find_all("li", recursive=False):
                a = c.find("a")
                if a and a.get_text(strip=True) == label:
                    return c
            raise ValueError(f"Could not find <li> with <a> text '{label}'")

        teachers_li = find_li("Docentes")
        classes_li = find_li("Turmas")
        rooms_li = find_li("Salas")

        return (
            self._extract_teacher_links(teachers_li),
            self._extract_classes_links(classes_li),
            rooms_li,
        )

    def get_teacher_page(self, path: str) -> TeacherPage:
        """Fetch and parse a teacher's schedule page.

        Extracts the teacher's abbreviation (sigla), full name, and code from
        the page header, then collects any red blocks (unavailable time slots).

        Args:
            path: Relative URL path to the teacher's schedule page.

        Returns:
            A ``DocentePage`` dict with keys ``sigla``, ``nome``, ``codigo``,
            and ``red_blocks``.

        Raises:
            ValueError: If the page header element is missing.
        """
        soup = self._request(path)
        td = soup.find("td", {"class": "cabtitulo"})
        if td is None:
            raise ValueError("Could not find <td class='cabtitulo'>")

        content = str(td.contents)
        if '"' in content:
            first = content.split('"')[1]
            abbreviation = content.split("<br/>, '")[1].split("'")[0]
            teachers_name = first[len(abbreviation) :] if abbreviation in first else ""
            teachers_code = content.split("<br/>, '")[2].split("'")[0]
        else:
            content = content.split("', <br/>, '")
            abbreviation = content[1].split("'")[0]
            teachers_name = (
                content[0][len(abbreviation) + 2 :]
                if abbreviation in content[0]
                else ""
            )
            teachers_code = content[2].split("'")[0]

        if " - " in teachers_name:
            teachers_name = teachers_name[3:]
        if teachers_name == "":
            teachers_name = abbreviation
        teachers_name = re.sub(r"[^\w\s]", "", teachers_name)

        return {
            "abbreviation": abbreviation,
            "name": teachers_name,
            "code": teachers_code,
            "red_blocks": self._extract_red_blocks(soup),
        }

    def get_red_blocks(self, path: str) -> list[tuple[int, str]]:
        """
        Extracts red block (time, day) pairs from a schedule page.
        """
        soup = self._request(path)
        return self._extract_red_blocks(soup)

    def get_class_page(self, path: str) -> dict[str, Any]:
        """
        Extracts all data from a turma schedule page.

        Returns a dict with keys: semanaIni, semanaFim, ucs, aulas, red_blocks.
        ucs maps UC sigla to [codigo, nome, numero_uc].
        aulas is a list of raw aula dicts (sigla, isTeorica, turmas, docentes,
        salas, hora, dia, semanaIni, semanaFim).
        red_blocks is a list of (time, day) tuples.
        """
        soup = self._request(path)

        # -- Get date (week) information ---------------------------------------
        weeks_tag = soup.find("td", {"class": "cabtitulo"})
        if weeks_tag is None:
            raise ValueError("Could not find 'cabtitulo' cell in schedule page")

        weeks = str(weeks_tag.contents[-1])
        dates = re.findall(r"\d{2}/\d{2}/\d{4}", weeks)
        if not dates:
            raise ValueError(f"Could not find dates in weeks string: {weeks!r}")

        start_date = datetime.strptime(dates[0], "%d/%m/%Y")
        end_date = datetime.strptime(dates[-1], "%d/%m/%Y")

        # -- Insert courses ----------------------------------------------------
        table = [str(row) for row in soup.find_all("table")[4].find_all("tr")[2:]]
        ucs = {}
        for row in table:
            row_items = row.split('<td align="left" valign="middle">')[1:]
            (codigo_nome, sigla, numero_uc) = (
                item.split("</td>")[0] for item in row_items
            )
            (codigo, nome) = codigo_nome.split(" - ", 1)
            ucs[sigla] = [codigo, nome, numero_uc]

        return {
            "start_date": start_date,
            "end_date": end_date,
            "ucs": ucs,
            "aulas": self._extract_aulas(soup, start_date, end_date),
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
