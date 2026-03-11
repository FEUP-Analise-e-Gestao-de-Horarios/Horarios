from typing import TypedDict


class Program(TypedDict):
    """A program entry parsed from the menu.

    Attributes:
        acronym: The program's acronym or abbreviation.
        name: The program's full name.
        years: The academic years belonging to this program, each containing their section links.
    """

    acronym: str
    name: str
    years: list[Year]


class Year(TypedDict):
    """An academic year belonging to a program, parsed from the menu.

    Attributes:
        number: The year number (e.g. 1, 2, 3).
        sections: The sections offered in this year, each containing their schedule links.
    """

    number: int
    sections: list[SectionLinks]


class SectionLinks(TypedDict):
    """A section entry parsed from the menu, with links to its schedule pages.

    Attributes:
        code: The section's identifier code.
        links: URLs to the section's schedule pages. Multiple links indicate different
            week ranges covered by separate schedule pages.
    """

    code: str
    links: list[str]
