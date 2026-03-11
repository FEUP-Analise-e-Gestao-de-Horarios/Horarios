from bs4 import BeautifulSoup
from bs4.element import Tag

from src.ingestion.schemas.programs import Program, SectionLinks, Year


def extract_menu_link(soup: BeautifulSoup) -> str:
    """Extract the src URL of the navigation frame from a frame-based page.

    Locates the `<frame name="links">` element and returns its `src` attribute,
    which points to the menu/navigation page.

    Args:
        soup: Parsed HTML of a frame-based page.

    Returns:
        The URL string of the navigation frame's src attribute.

    Raises:
        ValueError: If the `<frame name="links">` element is not found or its
            `src` attribute is not a string.
    """
    links = soup.find("frame", {"name": "links"})
    if links is None:
        raise ValueError("Could not find frame with name 'links'")

    src = links["src"]
    if not isinstance(src, str):
        raise ValueError(f"Expected 'src' to be a str, got {type(src)}")
    return src


def extract_menu_tags(menu_soup: BeautifulSoup) -> tuple[Tag, Tag, Tag]:
    """Extract the top-level menu section tags from the navigation page.

    Finds the `<ul id="menu">` element and locates the `<li>` items whose
    anchor text matches "Docentes", "Turmas", and "Salas".

    Args:
        menu_soup: Parsed HTML of the navigation/menu page.

    Returns:
        A tuple of three `<li>` tags: (teachers, classes, rooms).

    Raises:
        ValueError: If `<ul id="menu">` is not found, or if any of the expected
            section labels ("Docentes", "Turmas", "Salas") are missing.
    """
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
    return teachers_li, classes_li, rooms_li


def extract_teacher_links(docentes_menu: Tag) -> list[str]:
    """Extract all teacher page URLs from the Docentes menu section.

    Traverses the nested list structure inside the Docentes `<li>` tag.
    The expected structure is: `<li>` > `<ul>` > `<li>` (department) > `<ul>` > `<li>` (teacher) > `<a href="...">`.

    Args:
        docentes_menu: The `<li>` tag for the "Docentes" menu section,
            as returned by `extract_menu_tags`.

    Returns:
        A list of href URL strings, one per teacher page.

    Raises:
        ValueError: If any expected nested element (`<ul>`, `<li>`, `<a>`) is
            missing, or if an href attribute is not a string.
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


def extract_sessions_links(turmas_menu: Tag) -> list[Program]:
    """Parse the Turmas menu section into a structured list of programs.

    Traverses the deeply nested menu structure to build a list of `Program`
    objects. The expected hierarchy is:
    - Program (course acronym + name)
      - Year (year number)
        - Section/class (section code)
          - Week page URLs

    Args:
        turmas_menu: The `<li>` tag for the "Turmas" menu section,
            as returned by `extract_menu_tags`.

    Returns:
        A list of `Program` objects, each containing the course acronym, name,
        and a list of `Year` objects with their associated `SectionLinks`.

    Raises:
        ValueError: If any expected element in the menu hierarchy is missing,
            a text node cannot be parsed, or an href is not a string.
    """
    ul = turmas_menu.find("ul")
    if ul is None:
        raise ValueError("Could not find <ul> in turmas menu")

    result: list[Program] = []
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

        years: list[Year] = []
        for year in child_ul.find_all(recursive=False):
            year_a = year.find("a")
            if year_a is None:
                raise ValueError(
                    f"Could not find <a> in ano item for curso '{course_id}'",
                )

            year_number = int(str(year_a.contents[0]).split(" ")[1])

            plan_ul = year.find("ul")
            if plan_ul is None:
                raise ValueError(f"Could not find plano <ul> for ano '{year_number}'")

            plan_li = plan_ul.find("li")
            if plan_li is None:
                raise ValueError(
                    f"Could not find <li> in plano for ano '{year_number}'",
                )

            class_ul = plan_li.find("ul")
            if class_ul is None:
                raise ValueError(f"Could not find turmas <ul> for ano '{year_number}'")

            sections: list[SectionLinks] = []
            for class_ in class_ul.find_all(recursive=False):
                class_a = class_.find("a")
                if class_a is None:
                    raise ValueError(
                        f"Could not find <a> in turma item for ano '{year_number}'",
                    )

                section_code = str(class_a.contents[0])

                weeks_ul = class_.find("ul")
                if weeks_ul is None:
                    raise ValueError(
                        f"Could not find semanas <ul> for turma '{section_code}'",
                    )

                links: list[str] = []
                for week in weeks_ul.find_all("li"):
                    week_a = week.find("a", recursive=False)
                    if week_a is None:
                        raise ValueError(
                            f"Could not find <a> in semana item for turma '{section_code}'",
                        )

                    week_href = week_a["href"]
                    if not isinstance(week_href, str):
                        raise ValueError(
                            f"Expected href to be str, got {type(week_href)}",
                        )

                    links.append(week_href)
                sections.append({"code": section_code, "links": links})
            years.append({"number": year_number, "sections": sections})
        result.append({"acronym": course_id, "name": course_name, "years": years})
    return result
