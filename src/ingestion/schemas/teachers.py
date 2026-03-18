from typing import TypedDict

from src.ingestion.schemas.misc import RedBlock


class TeacherInfo(TypedDict):
    """Structured data extracted from a teacher's personal page.

    Attributes:
        acronym: Short identifier for the teacher (e.g. ``"ABC"``).
        name: Full display name of the teacher.
        code: Unique numeric identifier used by the institution.
        red_blocks: Schedule slots where the teacher is unavailable, each
            encoded as a ``(Time, WeekDay)`` pair.
    """

    acronym: str
    name: str
    code: int
    red_blocks: list[RedBlock]
