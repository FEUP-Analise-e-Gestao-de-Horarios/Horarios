import shutil
import sqlite3
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from src.ingestion.schemas.classes import Degree
from src.ingestion.schemas.misc import TurnosMap
from src.ingestion.schemas.rooms import RoomLinks
from src.ingestion.schemas.teachers import TeacherPages
from src.ingestion.scraper import Scraper
from src.projects.models import Project
from src.projects.projects_db.dao.class_dao import ClassDAO
from src.projects.projects_db.dao.class_red_block_dao import ClassRedBlockDAO
from src.projects.projects_db.dao.degree_dao import DegreeDAO
from src.projects.projects_db.dao.room_dao import RoomDAO
from src.projects.projects_db.dao.room_red_block_dao import RoomRedBlockDAO
from src.projects.projects_db.dao.session_dao import SessionDAO
from src.projects.projects_db.dao.subject_dao import SubjectDAO
from src.projects.projects_db.dao.teacher_dao import TeacherDAO
from src.projects.projects_db.dao.teacher_red_block_dao import TeacherRedBlockDAO
from src.projects.projects_db.dao.year_dao import YearDAO
from src.projects.projects_db.models.class_ import Class
from src.projects.projects_db.paths import general_db
from src.projects.projects_db.registry import get_session


class IngestionManager:
    """Orchestrates the full ingestion pipeline for a project.

    Connects to the project's SQLite database, drives the ``Scraper`` to
    fetch all schedule data, and delegates persistence to the individual
    ingestion functions. Manages project lifecycle timestamps and ensures the
    database and HTTP session are always closed, even on failure.
    """

    def __init__(self, proj_id: int):
        """Initialise the manager for the given project.

        Opens the project's SQLite database, creates a ``Scraper`` pointed at
        the project's URL, and initializes an empty degree shift map used during
        ingestion.

        Args:
            proj_id: Primary key of the ``Project`` to ingest.

        Raises:
            Project.DoesNotExist: If no project with ``proj_id`` exists.
        """
        self.proj_id = proj_id
        self.proj = Project.objects.get(pk=proj_id)

        self.path = Path(settings.PROJECTS_DB_PATH) / str(proj_id)
        self.conn = sqlite3.connect(self.path / "general_database.db")
        self.cursor: sqlite3.Cursor = self.conn.cursor()

        self.scraper = Scraper(self.proj.url)
        self.subject_shifts_map: TurnosMap = defaultdict(
            lambda: defaultdict(lambda: defaultdict(dict)),
        )

    def run(self) -> None:
        """Execute the full ingestion pipeline.

        Runs setup, pre-populates the red-blocks table, scrapes and ingests
        teachers, classes, and rooms, then runs post-processing steps. On
        success, calls ``_teardown_success``; on any exception, calls
        ``_teardown_failure`` and re-raises.
        """
        try:
            self._setup()

            teacher_links, degrees, rooms = self.scraper.read_menu()
            teacher_pages = self._ingest_classes(degrees)
            self._ingest_teachers(teacher_links, teacher_pages)
            self._ingest_rooms(rooms)
            self._ingest_sessions(degrees)
            self._ingest_shifts()

            self._teardown_success()

        except Exception:
            self._teardown_failure()
            raise

    # -----------------------------------------------------------------------
    # Setup / teardown
    # -----------------------------------------------------------------------

    def _setup(self) -> None:
        """Record ingestion start on the project and clear previous outcome timestamps."""
        self.proj.started_ingestion_at = timezone.now()
        self.proj.finished_ingestion_at = None
        self.proj.failed_ingestion_at = None
        self.proj.save()

    def _teardown_success(self) -> None:
        """Finalize a successful ingestion run.

        Copies ``general_database.db`` to ``initial_database.db`` as a
        baseline snapshot, records the completion timestamp, and closes the
        database connection and HTTP session.
        """
        shutil.copy2(
            self.path / "general_database.db",
            self.path / "initial_database.db",
        )
        self.proj.finished_ingestion_at = timezone.now()
        self.proj.save()
        self.conn.close()
        self.scraper.close()

    def _teardown_failure(self) -> None:
        """Record a failed ingestion run and release resources.

        Sets the failure timestamp on the project and closes the database
        connection and HTTP session.
        """
        self.proj.failed_ingestion_at = timezone.now()
        self.proj.save()
        self.conn.close()
        self.scraper.close()

    # -----------------------------------------------------------------------
    # Ingest functions
    # -----------------------------------------------------------------------

    def _ingest_teachers(
        self,
        teacher_links: list[str],
        teacher_pages: TeacherPages,
    ) -> None:
        """Ingest teacher records and their unavailability blocks into the DB.

        For each teacher link, fetches the schedule page, inserts the teacher
        into the ``docentes`` table (skipping duplicates), then maps each red
        block to its ``blocosVermelhos`` row and records it in ``blocoDocente``.

        Args:
            teacher_links: Relative URL paths to each teacher's schedule page.

        Raises:
            ValueError: If a red block's (time, day) pair has no matching row
                in the ``blocosVermelhos`` table.
        """
        teacher_red_blocks = dict(self.scraper.get_teacher_page(link) for link in teacher_links)

        with get_session(general_db(self.proj_id)) as session:
            teacher_dao = TeacherDAO(session)
            teacher_red_block_dao = TeacherRedBlockDAO(session)
            for code, teacher_page in teacher_pages.items():
                teacher = teacher_dao.create(
                    number=teacher_page["code"],
                    acronym=teacher_page["acronym"],
                    name=teacher_page["name"],
                )

                if teacher_red_blocks.get(code) is not None:
                    for red_block in teacher_red_blocks[code]:
                        teacher_red_block_dao.create(
                            teacher_id=teacher.id,
                            hour=red_block[0],
                            weekday=red_block[1],
                        )

            session.commit()

    def _ingest_classes(self, degrees: list[Degree]) -> TeacherPages:
        """Ingest degrees, classes, subjects, and sessions into the database.

        First inserts all degrees, then for each class fetches all weekly
        schedule pages, inserts red blocks (from the first page only, as they
        are week-invariant), and inserts subjects and sessions from every page.
        Theoretical sessions are also recorded in the internal shift map for
        later processing.

        Args:
            degrees: Structured degree hierarchy as returned by
                ``Scraper.read_menu``.

        Raises:
            ValueError: If a class has no schedule pages.
        """
        with get_session(general_db(self.proj_id)) as session_db:
            degree_dao = DegreeDAO(session_db)
            year_dao = YearDAO(session_db)
            class_dao = ClassDAO(session_db)
            class_red_block_dao = ClassRedBlockDAO(session_db)
            subject_dao = SubjectDAO(session_db)
            all_teachers: TeacherPages = {}

            for degree in degrees:
                degree_entry = degree_dao.create(
                    acronym=degree["acronym"],
                    name=degree["name"],
                )

                for year in degree["years"]:
                    year_entry = year_dao.create(
                        degree_id=degree_entry.id,
                        number=year["number"],
                    )

                    for class_ in year["classes"]:
                        class_entry = class_dao.create(
                            year_id=year_entry.id,
                            code=class_["code"],
                            shift=0,
                        )

                        class_pages, teacher_pages = self.scraper.get_class_pages(
                            class_,
                        )
                        all_teachers.update(teacher_pages)

                        for hour, weekday in class_pages[0]["red_blocks"]:
                            class_red_block_dao.create(
                                class_id=class_entry.id,
                                hour=hour,
                                weekday=weekday,
                            )

                        for class_page in class_pages:
                            for subject in class_page["subjects"]:
                                if subject_dao.get_by_code(subject["code"]) is None:
                                    subject_dao.create(
                                        year_id=year_entry.id,
                                        number=subject["number"],
                                        code=subject["code"],
                                        acronym=subject["acronym"],
                                        name=subject["name"],
                                    )
            session_db.commit()
        return all_teachers

    def _ingest_sessions(self, degrees: list[Degree]) -> None:
        with get_session(general_db(self.proj_id)) as session_db:
            session_dao = SessionDAO(session_db)
            subject_dao = SubjectDAO(session_db)
            for degree in degrees:
                for year in degree["years"]:
                    for class_ in year["classes"]:
                        for class_page in class_["class_pages"]:
                            subjects_by_acronym = {s["acronym"]: s for s in class_page["subjects"]}

                            for session in class_page["sessions"]:
                                rooms = session["room"] if session["room"][0] != "Online" else None

                                current_date = class_page["start_date"]
                                subject_code = subjects_by_acronym[session["subject_acronym"]][
                                    "code"
                                ]

                                while current_date <= class_page["end_date"]:
                                    session_entry = session_dao.get_by_class_with_attributes(
                                        week=current_date,
                                        weekday=session["weekday"],
                                        start_time=session["start_time"],
                                        duration=session["duration"],
                                        type=("T" if session["is_theoretical"] else "TP"),
                                        class_codes=session["classes"],
                                        teacher_numbers=session["teachers"],
                                        room_names=rooms,
                                    )
                                    if session_entry is None:
                                        session_dao.create(
                                            week=current_date,
                                            weekday=session["weekday"],
                                            start_time=session["start_time"],
                                            duration=session["duration"],
                                            type=("T" if session["is_theoretical"] else "TP"),
                                            room_names=rooms,
                                            class_codes=session["classes"],
                                            teacher_numbers=session["teachers"],
                                            subject_codes=[subject_code],
                                        )
                                    else:
                                        if not session_dao.has_subject(session_entry, subject_code):
                                            print(
                                                f"added subject to session with id {session_entry.id}",
                                            )
                                            subject_entry = subject_dao.get_by_code(subject_code)
                                            assert subject_entry is not None
                                            session_entry.subjects.append(subject_entry)

                                    current_date += timedelta(weeks=1)

            session_db.commit()

    def _ingest_rooms(self, rooms: list[RoomLinks]) -> None:
        """Ingest room metadata and unavailability blocks into the database.

        For each room, inserts its record and then fetches every timetable
        page to collect and store its red blocks.

        Args:
            rooms: Room entries as returned by ``Scraper.read_menu``.
        """
        with get_session(general_db(self.proj_id)) as session:
            room_dao = RoomDAO(session)
            room_red_block_dao = RoomRedBlockDAO(session)

            for room in rooms:
                room_entry = room_dao.create(
                    name=room["name"],
                    type=room["type_"],
                    size=room["size"],
                    seats=room["seats"],
                )

                for link in room["links"]:
                    for hour, weekday in self.scraper.get_room_page(link):
                        room_red_block_dao.create(
                            room_id=room_entry.id,
                            hour=hour,
                            weekday=weekday,
                        )
            session.commit()

    def _ingest_shifts(self) -> None:
        """
        Calculates and assigns shift numbers to classes based on their subject sessions.

        This method iterates through all subjects to identify sessions of type 'T' (Theoretical).
        It assigns a sequential shift number (starting from 1) to groups of classes found
        within these sessions. To ensure data integrity, each class is assigned a shift
        only once per ingestion cycle.

        Logic Flow:
            1.  Retrieves all subjects from the database.
            2.  For each subject, fetches all related 'T' type sessions.
            3.  For each session, identifies classes that have not yet been processed
                (using a 'visited' set).
            4.  Assigns the current `shift` counter value to the `shift` attribute of
                the class model.
            5.  Increments the `shift` counter only after a session with new,
                unprocessed classes is handled.
            6.  Persists all changes to the database in a single transaction.
        """
        with get_session(general_db(self.proj_id)) as session_db:
            session_dao = SessionDAO(session_db)
            subject_dao = SubjectDAO(session_db)

            subjects = subject_dao.get_all()
            visited_classes: set[Class] = set()

            for subject in subjects:
                shift = 1
                sessions = session_dao.get_by_subject_type(subject, "T")

                for session in sessions:
                    classes = set(session.classes)
                    classes_no_shift = classes.difference(visited_classes)

                    if len(classes_no_shift) == 0:
                        continue

                    for class_ in classes_no_shift:
                        class_.shift = shift
                        visited_classes.add(class_)

                        print(f"Class {class_.code} with shift {shift}")

                    shift += 1

            session_db.commit()
