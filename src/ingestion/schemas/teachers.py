from typing import TypedDict


class TeacherPage(TypedDict):
    """Structured data extracted from a teacher's personal page.

    Attributes:
        acronym: Short identifier for the teacher (e.g. ``"ABC"``).
        name: Full display name of the teacher.
        code: Unique numeric or alphanumeric identifier used by the institution.
    """

    code: int
    acronym: str
    name: str


TeacherPages = dict[int, TeacherPage]
"""
Maps each teacher to the respective unique code

Structure:
    TeachersPage[TeacherPage.code] = TeacherPage
"""
