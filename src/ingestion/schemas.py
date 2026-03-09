from collections.abc import Sequence
from datetime import datetime
from typing import TypedDict

from bs4 import Tag

Matrix = Sequence[Sequence[Tag]]

Time = int
WeekDay = str
RedBlock = tuple[Time, WeekDay]

# -------------------------------------------------------------------
# Link Extraction - Teachers
# -------------------------------------------------------------------


class TeacherLinks(TypedDict):
    abbreviation: str
    name: str
    code: str
    red_blocks: list[RedBlock]


# -------------------------------------------------------------------
# Link Extraction - Courses
# -------------------------------------------------------------------


class ClassLinks(TypedDict):
    code: str
    links: list[str]


class YearLinks(TypedDict):
    number: int
    classes: list[ClassLinks]


class CourseLinks(TypedDict):
    abbreviation: str
    name: str
    years: list[YearLinks]


# -------------------------------------------------------------------
# Link Extraction - Classes
# -------------------------------------------------------------------


class ClassSchedule(TypedDict):
    start_date: datetime
    end_date: datetime
    red_blocks: list[RedBlock]
