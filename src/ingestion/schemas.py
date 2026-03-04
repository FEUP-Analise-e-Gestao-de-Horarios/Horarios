from collections.abc import Sequence
from datetime import datetime
from typing import TypedDict

from bs4 import Tag

Matrix = Sequence[Sequence[Tag]]

Time = int
WeekDay = str
RedBlock = tuple[Time, WeekDay]


class TeacherPage(TypedDict):
    abbreviation: str
    name: str
    code: str
    red_blocks: list[RedBlock]


class ClassPages(TypedDict):
    code: str
    links: list[str]


class YearInfo(TypedDict):
    number: int
    classes: list[ClassPages]


class CourseInfo(TypedDict):
    abbreviation: str
    name: str
    years: list[YearInfo]


class ClassSchedule(TypedDict):
    start_date: datetime
    end_date: datetime
    red_blocks: list[RedBlock]
