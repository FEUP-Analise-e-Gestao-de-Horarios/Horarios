from datetime import datetime
from typing import TypedDict

from src.ingestion.schemas.misc import RedBlock, WeekDay


class SectionPage(TypedDict):
    start_date: datetime
    end_date: datetime
    courses: list[Course]
    sessions: list[Session]
    red_blocks: list[RedBlock]


class Course(TypedDict):
    code: str
    name: str
    acronym: str
    number: int


class Session(TypedDict):
    course_acronym: str
    weekday: WeekDay
    start_time: int
    duration: int
    teachers: list[int]
    sections: list[str]
    room: list[str]
    is_theoretical: bool
