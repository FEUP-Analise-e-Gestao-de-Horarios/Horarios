from typing import Any

import requests
from bs4 import BeautifulSoup, Tag

from src.ingestion.parsers.menu import (
    extract_menu_link,
    extract_menu_tags,
    extract_sessions_links,
    extract_teacher_links,
)
from src.ingestion.parsers.red_blocks import extract_red_blocks
from src.ingestion.parsers.section_page import (
    extract_courses,
    extract_sessions,
    extract_week_dates,
)
from src.ingestion.parsers.teacher_page import extract_teacher_info
from src.ingestion.schemas.programs import Program
from src.ingestion.schemas.sections import SectionPage
from src.ingestion.schemas.teachers import TeacherPage


class Scraper:
    _DEFAULT_TIMEOUT: int = 30

    def __init__(self, base_url: str) -> None:
        """Initialise the scraper with a base URL.

        Args:
            base_url: Root URL of the schedule website. All relative paths
                returned by other methods are resolved against this URL.
        """
        self.base_url = base_url
        self._session = requests.Session()

    # -------------------------------------------------------------------
    # Internal request helper
    # -------------------------------------------------------------------

    def _request(self, path: str) -> BeautifulSoup:
        """Make an HTTP GET request and return the parsed response.

        Appends *path* to :attr:`base_url`, sends the request using the
        shared session, and raises on non-2xx status codes.

        Args:
            path: Relative URL path to append to the base URL.

        Returns:
            A ``BeautifulSoup`` object parsed from the response body.

        Raises:
            requests.HTTPError: If the server returns a non-2xx status code.
        """
        response = self._session.get(
            self.base_url + path,
            timeout=self._DEFAULT_TIMEOUT,
        )
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")

    # -------------------------------------------------------------------
    # Public page-navigation methods
    # -------------------------------------------------------------------

    def read_menu(self) -> tuple[list[str], list[Program], Tag]:
        soup = self._request("")
        menu_link = extract_menu_link(soup)

        menu_soup = self._request(menu_link)
        teachers_li, classes_li, rooms_li = extract_menu_tags(menu_soup)

        return (
            extract_teacher_links(teachers_li),
            extract_sessions_links(classes_li),
            rooms_li,  # TODO Clean this up
        )

    def get_teacher_page(self, path: str) -> TeacherPage:
        soup = self._request(path)
        acronym, name, code = extract_teacher_info(soup)
        red_blocks = extract_red_blocks(soup)

        return {
            "acronym": acronym,
            "name": name,
            "code": code,
            "red_blocks": red_blocks,
        }

    def get_section_page(self, path: str) -> SectionPage:
        soup = self._request(path)

        start_date, end_date = extract_week_dates(soup)
        courses = extract_courses(soup)
        sessions = extract_sessions(soup)
        red_blocks = extract_red_blocks(soup)

        return {
            "start_date": start_date,
            "end_date": end_date,
            "courses": courses,
            "sessions": sessions,
            "red_blocks": red_blocks,
        }

    # -------------------------------------------------------------------
    # Others
    # -------------------------------------------------------------------

    def close(self) -> None:
        """Closes the HTTP session."""
        self._session.close()

    # TODO CHECK --------------------------------------------------------

    def get_red_blocks(self, path: str) -> list[tuple[int, str]]:
        """
        Extracts red block (time, day) pairs from a schedule page.
        """
        soup = self._request(path)
        return extract_red_blocks(soup)

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
                },
            )
        return result
