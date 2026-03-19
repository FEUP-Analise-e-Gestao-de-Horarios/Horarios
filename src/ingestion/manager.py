import shutil
import sqlite3
import uuid
from collections import defaultdict
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.utils import timezone
from sqlalchemy.exc import IntegrityError

from src.ingestion.schemas.classes import Degree, Teacher
from src.ingestion.schemas.misc import TurnosMap
from src.ingestion.schemas.rooms import RoomInfo
from src.ingestion.scraper import Scraper
from src.projects.models import Project
from src.projects.projects_db.dao import ClassRedBlockDAO
from src.projects.projects_db.dao.class_dao import ClassDAO
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

            # Load info from class pages
            for degree in degrees:
                for year in degree["years"]:
                    for class_ in year["classes"]:
                        for link in class_["links"]:
                            class_["pages"].append(self.scraper.get_class_page(link))

            # Extract teachers from class pages.
            # This is necessary as some teachers don't have red blocks
            # which means they didn't have any links on the menu.
            # These will be added to the ones extracted from the menu.
            teachers_from_class_pages = [
                teacher
                for degree in degrees
                for year in degree["years"]
                for class_ in year["classes"]
                for class_page in class_["pages"]
                for teacher in class_page["teachers"]
            ]

            self._ingest_teachers(teacher_links, teachers_from_class_pages)
            self._ingest_classes(degrees)
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
        teachers_from_classes_page: list[Teacher],
    ) -> None:
        """Ingest teacher records and their unavailability blocks into the DB.

        For each teacher link, fetches the schedule page, inserts the teacher
        into the ``docentes`` table (skipping duplicates), then maps each red
        block to its ``blocosVermelhos`` row and records it in ``blocoDocente``.

        Teachers that appear on class pages but not in the menu (i.e. those
        without red blocks) are merged in from ``teachers_from_classes_page``.

        Args:
            teacher_links: Relative URL paths to each teacher's schedule page.
            teachers_from_classes_page: Teacher entries extracted from class
                pages, used to supplement teachers missing from the menu.

        Raises:
            ValueError: If a red block's (time, day) pair has no matching row
                in the ``blocosVermelhos`` table.
        """
        teachers = [self.scraper.get_teacher_page(link) for link in teacher_links]

        # Add missing teachers (didn't have red blocks so no links were available)
        existing_codes = {t["code"] for t in teachers}
        for teacher in teachers_from_classes_page:
            if teacher["code"] not in existing_codes:
                teachers.append({**teacher, "red_blocks": []})
                existing_codes.add(teacher["code"])

        with get_session(general_db(self.proj_id)) as session:
            teacher_dao = TeacherDAO(session)
            teacher_red_block_dao = TeacherRedBlockDAO(session)

            for teacher in teachers:
                teacher_entry = teacher_dao.create(
                    number=teacher["code"],
                    acronym=teacher["acronym"],
                    name=teacher["name"],
                )

                for hour, weekday in teacher["red_blocks"]:
                    teacher_red_block_dao.create(
                        teacher_id=teacher_entry.id,
                        hour=hour,
                        weekday=weekday,
                    )

            session.commit()

    def _ingest_classes(self, degrees: list[Degree]) -> None:
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
                        class_dao.create(
                            year_id=year_entry.id,
                            code=class_["code"],
                            shift=0,
                        )

            session_db.commit()

    def _ingest_rooms(self, rooms: list[RoomInfo]) -> None:
        """Ingest room metadata and unavailability blocks into the database.

        For each room, inserts its record and then fetches a timetable page
        to collect and store its red blocks.

        Args:
            rooms: Room entries as returned by ``Scraper.read_menu``.
        """

        rooms_data = [(room, self.scraper.get_room_page(room["link"])) for room in rooms]

        with get_session(general_db(self.proj_id)) as session:
            room_dao = RoomDAO(session)
            room_red_block_dao = RoomRedBlockDAO(session)

            for room, red_blocks in rooms_data:
                room_entry = room_dao.create(
                    name=room["name"],
                    type=room["type_"],
                    size=room["size"],
                    seats=room["seats"],
                )

                for hour, weekday in red_blocks:
                    room_red_block_dao.create(
                        room_id=room_entry.id,
                        hour=hour,
                        weekday=weekday,
                    )

            session.commit()

    def _ingest_sessions(self, degrees: list[Degree]) -> None:
        """Ingest session records from all class pages into the database.

        Iterates over every class page within the degree hierarchy. For each
        session, resolves its subject, teachers, classes, and rooms to database
        entries, then creates weekly session records spanning the page's date
        range. If a session already exists for the same week, weekday, time,
        and classes, its subject list is extended rather than creating a
        duplicate.

        Args:
            degrees: Structured degree hierarchy with populated ``pages``.

        Raises:
            ValueError: If a referenced year, subject, teacher, class, or room
                cannot be found in the database.
        """
        with get_session(general_db(self.proj_id)) as db_session:
            session_dao = SessionDAO(db_session)
            year_dao = YearDAO(db_session)
            class_red_block_dao = ClassRedBlockDAO(db_session)
            subject_dao = SubjectDAO(db_session)
            teacher_dao = TeacherDAO(db_session)
            class_dao = ClassDAO(db_session)
            room_dao = RoomDAO(db_session)
            for degree in degrees:
                for year in degree["years"]:
                    year_db_entry = year_dao.get_by_degree_and_number(
                        degree_acronym=degree["acronym"],
                        number=year["number"],
                    )
                    if not year_db_entry:
                        raise ValueError(
                            f"Year {year['number']} not found for degree {degree['acronym']}",
                        )

                    for class_ in year["classes"]:
                        class_db_entry = class_dao.get_by_code(class_["code"])
                        if not class_db_entry:
                            raise ValueError(f"Class {class_['code']} not found")

                        first_class_page = class_["pages"][0]
                        if not first_class_page:
                            raise ValueError(f"No pages found for class {class_['code']}")

                        for hour, weekday in first_class_page["red_blocks"]:
                            class_red_block_dao.create(
                                class_id=class_db_entry.id,
                                hour=hour,
                                weekday=weekday,
                            )

                        for class_page in class_["pages"]:
                            subjects_by_acronym = {s["acronym"]: s for s in class_page["subjects"]}

                            subjects_db_entries = subject_dao.get_by_numbers(
                                {s["number"] for s in class_page["subjects"]},
                                check_count=False,
                            )
                            subjects_db_numbers = {s.number for s in subjects_db_entries}
                            for subject in subjects_by_acronym.values():
                                if subject["number"] not in subjects_db_numbers:
                                    subject_dao.create(
                                        year_id=year_db_entry.id,
                                        number=subject["number"],
                                        code=subject["code"],
                                        acronym=subject["acronym"],
                                        name=subject["name"],
                                    )

                            for session in class_page["sessions"]:
                                current_date = class_page["start_date"]
                                original_block_id = uuid.uuid7()

                                subject_number = subjects_by_acronym[session["subject_acronym"]][
                                    "number"
                                ]
                                subject_db_entry = subject_dao.get_by_number(subject_number)
                                if not subject_db_entry:
                                    raise ValueError(
                                        f"Subject {subject_number} not found for year {year['number']} of degree {degree['acronym']}",
                                    )
                                subject_ids = {subject_db_entry.id}

                                teachers = teacher_dao.get_by_numbers(set(session["teachers"]))
                                teacher_ids = {teacher.id for teacher in teachers}

                                classes = class_dao.get_by_codes(set(session["classes"]))
                                class_ids = {class_.id for class_ in classes}

                                rooms = (
                                    room_dao.get_by_names(set(session["rooms"]))
                                    if session["rooms"][0] != "Online"
                                    else []
                                )
                                room_ids = {room.id for room in rooms}

                                while current_date <= class_page["end_date"]:
                                    try:
                                        with db_session.begin_nested():
                                            session_dao.create(
                                                week=current_date,
                                                weekday=session["weekday"],
                                                start_time=session["start_time"],
                                                duration=session["duration"],
                                                type_=("T" if session["is_theoretical"] else "TP"),
                                                original_block_id=original_block_id,
                                                subject_ids=subject_ids,
                                                teacher_ids=teacher_ids,
                                                class_ids=class_ids,
                                                room_ids=room_ids,
                                            )
                                    except IntegrityError:
                                        session_db_entry = session_dao.get_by_week_and_block(
                                            week=current_date,
                                            original_block_id=original_block_id,
                                        )
                                        if session_db_entry is None:
                                            raise

                                        if subject_db_entry not in session_db_entry.subjects:
                                            session_db_entry.subjects.append(subject_db_entry)

                                    current_date += timedelta(weeks=1)

            db_session.commit()

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

                    shift += 1

            session_db.commit()
