from typing import TypedDict

from src.ingestion.schemas.misc import RedBlock


class TeacherPage(TypedDict):
    """Structured data extracted from a teacher's personal page.

    Attributes:
        acronym: Short identifier for the teacher (e.g. ``"ABC"``).
        name: Full display name of the teacher.
        code: Unique numeric or alphanumeric identifier used by the institution.
        red_blocks: Schedule slots where the teacher is unavailable, each
            encoded as a ``(Time, WeekDay)`` pair.
    """

    code: int
    acronym: str
    name: str
    red_blocks: list[RedBlock]
