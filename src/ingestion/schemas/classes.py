from datetime import date
from typing import TypedDict

from src.ingestion.schemas.misc import RedBlock, WeekDay


class Degree(TypedDict):
    """A degree entry parsed from the menu.

    Attributes:
        acronym: The degree's acronym or abbreviation.
        name: The degree's full name.
        years: The academic years belonging to this degree, each containing their class links.
    """

    acronym: str
    name: str
    years: list[Year]


class Year(TypedDict):
    """An academic year belonging to a degree, parsed from the menu.

    Attributes:
        number: The year number (e.g. 1, 2, 3).
        classes: The classes offered in this year, each containing their schedule links.
    """

    number: int
    classes: list[Class]


class Class(TypedDict):
    """A class entry parsed from the menu, with links to its schedule pages.

    Attributes:
        code: The class's identifier code.
        links: URLs to the class's schedule pages. Multiple links indicate different
            week ranges covered by separate schedule pages.
        pages: Parsed schedule page data, populated during ingestion by fetching
            each URL in ``links``.
    """

    code: str
    links: list[str]
    pages: list[ClassPage]


class ClassPage(TypedDict):
    """All data extracted from a single class schedule page.

    Attributes:
        start_date: First day of the schedule week covered by the page.
        end_date: Last day of the schedule week covered by the page.
        teachers: Teachers listed on the class schedule page.
        subjects: Subjects associated with the class for this week.
        sessions: Scheduled sessions parsed from the timetable.
        red_blocks: Unavailable time slots marked on the timetable.
    """

    start_date: date
    end_date: date
    teachers: list[Teacher]
    subjects: list[Subject]
    sessions: list[Session]
    red_blocks: list[RedBlock]


class Teacher(TypedDict):
    """A teacher entry parsed from a class schedule page.

    Attributes:
        acronym: Short identifier for the teacher (e.g. ``"ABC"``).
        name: Full display name of the teacher.
        code: Unique numeric identifier used by the institution.
    """

    acronym: str
    name: str
    code: int


class Subject(TypedDict):
    """A subject associated with a class, parsed from a class schedule page.

    Attributes:
        code: The subject's institutional code.
        name: The subject's full name.
        acronym: The subject's short abbreviation.
        number: Number of students enrolled in this class for the subject.
    """
                        
    code: str
    name: str
    acronym: str
    number: int


class Session(TypedDict):
    """A single scheduled session parsed from a class timetable.

    Attributes:
        subject_acronym: Acronym of the subject this session belongs to.
        weekday: Day of the week on which the session takes place.
        start_time: Start time encoded as ``HHMM`` (see :data:`~src.ingestion.schemas.misc.Time`).
        duration: Duration in timetable row slots (the cell's ``rowspan`` value).
        teachers: Numeric codes of the teachers assigned to this session.
        classes: Class codes participating in this session.
        rooms: Names of the rooms where the session takes place. Contains
            ``["Online"]`` when no room is listed in the session block.
        is_theoretical: ``True`` if the session is theoretical
            (CSS class ``td_tipologia_19``), ``False`` otherwise.
    """

    subject_acronym: str
    weekday: WeekDay
    start_time: int
    duration: int
    teachers: list[int]
    classes: list[str]
    rooms: list[str]
    is_theoretical: bool
