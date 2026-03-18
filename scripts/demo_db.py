"""Demo script: creates a SQLite DB and exercises the DAOs."""

import datetime
from pathlib import Path

from src.projects.projects_db.dao import (
    ClassDAO,
    DegreeDAO,
    RoomDAO,
    SessionDAO,
    SubjectDAO,
    TeacherDAO,
    YearDAO,
)
from src.projects.projects_db.registry import evict_engine, get_session, init_engine
from src.projects.projects_db.schemas.weekday import WeekDay

DB_PATH = Path("demo.db")


def main() -> None:
    init_engine(DB_PATH)

    with get_session(DB_PATH) as session:
        degree_dao = DegreeDAO(session)
        year_dao = YearDAO(session)
        subject_dao = SubjectDAO(session)
        class_dao = ClassDAO(session)
        teacher_dao = TeacherDAO(session)
        room_dao = RoomDAO(session)
        session_dao = SessionDAO(session)

        # --- Create objects ---
        print("Creating degree...")
        degree = degree_dao.create(
            acronym="LEIC",
            name="Licenciatura em Engenharia Informática e Computadores",
        )

        print("Creating year...")
        year = year_dao.create(degree_id=degree.id, number=1)

        print("Creating subject...")
        subject = subject_dao.create(
            year_id=year.id,
            number=101,
            code="LEIC-101",
            acronym="PROG",
            name="Programação",
        )

        print("Creating class...")
        cls = class_dao.create(year_id=year.id, code="LEIC-1-D", shift=1)

        print("Creating teacher...")
        teacher = teacher_dao.create(number=42, acronym="JOS", name="João Silva")

        print("Creating room...")
        room = room_dao.create(name="A101", type="lab", size="medium", seats="30")

        print("Creating session...")
        week = datetime.date(2026, 3, 16)
        _sess = session_dao.create(
            week=week,
            weekday=WeekDay.MONDAY,
            start_time=8,
            duration=2,
            type_="T",
            room_ids=[room.id],
            teacher_ids=[teacher.id],
            subject_ids=[subject.id],
            class_ids=[cls.id],
        )

        session.commit()
        print("All objects committed.\n")

        # --- Retrieve and print ---
        print(f"Degree:  {degree_dao.get_by_acronym('LEIC')}")
        print(f"Year:    {year_dao.get_by_degree_and_number(degree_acronym='LEIC', number=1)}")
        print(f"Subject: {subject_dao.get_by_code('LEIC-101')}")
        print(f"Class:   {class_dao.get_by_code('LEIC-1-D')}")
        print(f"Teacher: {teacher_dao.get_by_acronym('JOS')}")
        print(f"Room:    {room_dao.get_by_name('A101')}")

        sessions_for_week = session_dao.get_by_week(week)
        print(f"Sessions for week {week}: {sessions_for_week}")

        sessions_for_teacher = session_dao.get_by_teacher(teacher.id)
        print(f"Sessions for teacher {teacher.acronym}: {sessions_for_teacher}")

    evict_engine(DB_PATH)
    DB_PATH.unlink(missing_ok=True)
    DB_PATH.with_suffix(".db-wal").unlink(missing_ok=True)
    DB_PATH.with_suffix(".db-shm").unlink(missing_ok=True)


if __name__ == "__main__":
    main()
