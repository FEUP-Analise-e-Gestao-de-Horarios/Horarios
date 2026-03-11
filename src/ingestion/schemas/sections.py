from datetime import date
from typing import TypedDict

from src.ingestion.schemas.misc import RedBlock, WeekDay


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


class SectionPage(TypedDict):
    """All data extracted from a single section schedule page.

    Attributes:
        start_date: First day of the schedule week covered by the page.
        end_date: Last day of the schedule week covered by the page.
        courses: Courses associated with the section for this week.
        sessions: Scheduled sessions parsed from the timetable.
        red_blocks: Unavailable time slots marked on the timetable.
    """

    start_date: date
    end_date: date
    courses: list[Course]
    sessions: list[Session]
    red_blocks: list[RedBlock]


class Course(TypedDict):
    """A course associated with a section, parsed from a section schedule page.

    Attributes:
        code: The course's institutional code.
        name: The course's full name.
        acronym: The course's short abbreviation.
        number: Number of students enrolled in this section for the course.
    """

    code: str
    name: str
    acronym: str
    number: int


class Session(TypedDict):
    """A single scheduled session parsed from a section timetable.

    Attributes:
        course_acronym: Acronym of the course this session belongs to.
        weekday: Day of the week on which the session takes place.
        start_time: Start time encoded as ``HHMM`` (see :data:`~src.ingestion.schemas.misc.Time`).
        duration: Duration in timetable row slots (the cell's ``rowspan`` value).
        teachers: Numeric codes of the teachers assigned to this session.
        sections: Section codes participating in this session.
        room: Names of the rooms where the session takes place. Contains
            ``["Online"]`` when no room is listed in the session block.
        is_theoretical: ``True`` if the session is theoretical
            (CSS class ``td_tipologia_19``), ``False`` otherwise.
    """

    course_acronym: str
    weekday: WeekDay
    start_time: int
    duration: int
    teachers: list[int]
    sections: list[str]
    room: list[str]
    is_theoretical: bool
