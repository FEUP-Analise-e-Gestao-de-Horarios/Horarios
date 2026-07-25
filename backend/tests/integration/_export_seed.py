"""Seeding helpers for the exporter integration tests.

The exporter compares two per-project SQLite files, ``initial_database.db`` (the
baseline) and ``general_database.db`` (the current, edited timetable). These
helpers seed a fixed set of reference rows (degree/year/subjects/classes/rooms/
teachers) with **stable ids** into each database, then let a test place sessions
that reference those ids. Because both databases share the same reference ids, a
test only has to vary the sessions to produce a move, exchange, resource change,
addition or removal.

Not a ``test_*`` module, so pytest never collects it.
"""

import datetime
import uuid
from collections.abc import Iterable

from sqlalchemy.orm import Session

from src.projects.projects_db.models._secondary_tables import session_rooms, session_teachers
from src.projects.projects_db.models.session_class_subject import SessionClassSubject
from src.projects.projects_db.schemas.weekday import WeekDay
from tests.factories import (
    make_class,
    make_degree,
    make_room,
    make_session,
    make_subject,
    make_teacher,
    make_year,
)

WEEK = datetime.date(2026, 1, 5)
WEEK_2 = datetime.date(2026, 1, 12)
WEEK_3 = datetime.date(2026, 1, 19)


def uid(value: int) -> uuid.UUID:
    """Return a deterministic UUID for a small integer."""
    return uuid.UUID(int=value)


# Fixed reference ids, shared across the initial and general databases.
DEGREE_ID = uid(1)
YEAR_ID = uid(2)
SUBJECT_A = uid(10)
SUBJECT_B = uid(11)
CLASS_A = uid(20)
CLASS_B = uid(21)
ROOM_A = uid(30)
ROOM_B = uid(31)
TEACHER_A = uid(40)
TEACHER_B = uid(41)

ROOM_A_NAME = "B101"
ROOM_B_NAME = "B102"


def seed_reference_data(session: Session) -> None:
    """Insert the fixed degree/year/subjects/classes/rooms/teachers into a DB."""
    degree = make_degree(session, id=DEGREE_ID, commit=False)
    year = make_year(session, degree=degree, id=YEAR_ID, number=1, commit=False)
    make_subject(
        session,
        year=year,
        id=SUBJECT_A,
        number=1,
        code="IA001",
        acronym="IA",
        name="Inteligencia Artificial",
        commit=False,
    )
    make_subject(
        session,
        year=year,
        id=SUBJECT_B,
        number=2,
        code="ES001",
        acronym="ES",
        name="Engenharia de Software",
        commit=False,
    )
    make_class(session, year=year, id=CLASS_A, code="1LEIC01", shift=1, commit=False)
    make_class(session, year=year, id=CLASS_B, code="1LEIC02", shift=2, commit=False)
    make_room(session, id=ROOM_A, name=ROOM_A_NAME, commit=False)
    make_room(session, id=ROOM_B, name=ROOM_B_NAME, commit=False)
    make_teacher(session, id=TEACHER_A, number=1, acronym="AA", name="Ada Alpha", commit=False)
    make_teacher(session, id=TEACHER_B, number=2, acronym="BB", name="Bruno Beta", commit=False)
    session.commit()


def seed_session(
    session: Session,
    *,
    session_id: uuid.UUID,
    start_time: int,
    original_block_id: uuid.UUID,
    week: datetime.date = WEEK,
    weekday: WeekDay = WeekDay.MONDAY,
    duration: int = 2,
    type_: str = "T",
    rooms: Iterable[uuid.UUID] = (ROOM_A,),
    teachers: Iterable[uuid.UUID] = (TEACHER_A,),
    class_subjects: Iterable[tuple[uuid.UUID, uuid.UUID]] = ((CLASS_A, SUBJECT_A),),
    commit: bool = True,
) -> uuid.UUID:
    """Insert one session and its room/teacher/class-subject associations."""
    make_session(
        session,
        id=session_id,
        week=week,
        weekday=weekday,
        start_time=start_time,
        duration=duration,
        type=type_,
        original_block_id=original_block_id,
        commit=False,
    )
    for room_id in rooms:
        session.execute(
            session_rooms.insert().values(session_id=session_id, room_id=room_id),
        )
    for teacher_id in teachers:
        session.execute(
            session_teachers.insert().values(session_id=session_id, teacher_id=teacher_id),
        )
    for class_id, subject_id in class_subjects:
        session.add(
            SessionClassSubject(
                session_id=session_id,
                class_id=class_id,
                subject_id=subject_id,
            ),
        )
    if commit:
        session.commit()
    else:
        session.flush()
    return session_id
