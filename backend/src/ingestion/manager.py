import shutil
import uuid
from collections import defaultdict
from datetime import timedelta

from django.utils import timezone

from src.ingestion.schemas.classes import Degree, Teacher
from src.ingestion.schemas.misc import TurnosMap
from src.ingestion.schemas.rooms import RoomInfo
from src.ingestion.scraper import Scraper
from src.ingestion.utils import extract_teachers_from_class_pages, load_class_pages
from src.projects.models import Project
from src.projects.projects_db.dao import (
    ClassDAO,
    ClassRedBlockDAO,
    DegreeDAO,
    RoomDAO,
    RoomRedBlockDAO,
    SessionClassSubjectDAO,
    SessionDAO,
    SubjectDAO,
    TeacherDAO,
    TeacherRedBlockDAO,
    YearDAO,
)
from src.projects.projects_db.models import Class, Room, Subject, Year
from src.projects.projects_db.models import Teacher as TeacherModel
from src.projects.projects_db.paths import general_db, initial_db
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
        self.db_session = get_session(general_db(self.proj_id))

        self.scraper = Scraper(self.proj.url)
        self.subject_shifts_map: TurnosMap = defaultdict(
            lambda: defaultdict(lambda: defaultdict(dict)),
        )

        # Maps to speed up data lookup
        #  - Teacher.code -> Teacher
        #  - (Degree.acronym, Year.number) -> Year
        #  - Class.code -> Class
        #  - Room.name -> Room
        #  - Subject.number -> Subject
        self.teacher_entries: dict[int, TeacherModel] = {}
        self.year_entries: dict[tuple[str, int], Year] = {}
        self.class_entries: dict[str, Class] = {}
        self.room_entries: dict[str, Room] = {}
        self.subject_entries: dict[int, Subject] = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.db_session.close()

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

            load_class_pages(degrees, self.scraper)
            teachers_from_class_pages = extract_teachers_from_class_pages(degrees)

            self._ingest_teachers(teacher_links, teachers_from_class_pages)
            self._ingest_classes(degrees)
            self._ingest_rooms(rooms)

            self._ingest_sessions(degrees)
            self._ingest_shifts()

            # -- Snapshot general_db into init_db ----------------------------------
            self.db_session.close()
            shutil.copy2(general_db(self.proj_id), initial_db(self.proj_id))

            self._teardown_success()

        except Exception:
            self._teardown_failure()
            raise

    # -----------------------------------------------------------------------
    # Setup / teardown
    # -----------------------------------------------------------------------

    def _setup(self) -> None:
        """Record ingestion start on the project and clear previous outcome timestamps."""
        self.proj.ingestion_started_at = timezone.now()
        self.proj.ingestion_finished_at = None
        self.proj.ingestion_failed_at = None
        self.proj.save()

    def _teardown_success(self) -> None:
        """Finalize a successful ingestion run.

        Copies ``general_database.db`` to ``initial_database.db`` as a
        baseline snapshot, records the completion timestamp, and closes the
        database connection and HTTP session.
        """
        self.proj.ingestion_finished_at = timezone.now()
        self.proj.save()
        self.scraper.close()

    def _teardown_failure(self) -> None:
        """Record a failed ingestion run and release resources.

        Sets the failure timestamp on the project and closes the database
        connection and HTTP session.
        """
        self.proj.ingestion_failed_at = timezone.now()
        self.proj.save()
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

        teacher_dao = TeacherDAO(self.db_session)
        teacher_red_block_dao = TeacherRedBlockDAO(self.db_session)

        for teacher in teachers:
            teacher_entry = teacher_dao.create(
                number=teacher["code"],
                acronym=teacher["acronym"],
                name=teacher["name"],
            )
            self.teacher_entries[teacher["code"]] = teacher_entry

            for hour, weekday in teacher["red_blocks"]:
                teacher_red_block_dao.create(
                    teacher_id=teacher_entry.id,
                    hour=hour,
                    weekday=weekday,
                )

        self.db_session.commit()

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

        degree_dao = DegreeDAO(self.db_session)
        year_dao = YearDAO(self.db_session)
        class_dao = ClassDAO(self.db_session)

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
                self.year_entries[(degree["acronym"], year["number"])] = year_entry

                for class_ in year["classes"]:
                    class_entry = class_dao.create(
                        year_id=year_entry.id,
                        code=class_["code"],
                        shift=0,
                    )
                    self.class_entries[class_["code"]] = class_entry

        self.db_session.commit()

    def _ingest_rooms(self, rooms: list[RoomInfo]) -> None:
        """Ingest room metadata and unavailability blocks into the database.

        For each room, inserts its record and then fetches a timetable page
        to collect and store its red blocks.

        Args:
            rooms: Room entries as returned by ``Scraper.read_menu``.
        """

        rooms_data = [(room, self.scraper.get_room_page(room["link"])) for room in rooms]

        room_dao = RoomDAO(self.db_session)
        room_red_block_dao = RoomRedBlockDAO(self.db_session)

        for room, red_blocks in rooms_data:
            room_entry = room_dao.create(
                name=room["name"],
                type=room["type_"],
                size=room["size"],
                seats=room["seats"],
            )
            self.room_entries[room["name"]] = room_entry

            for hour, weekday in red_blocks:
                room_red_block_dao.create(
                    room_id=room_entry.id,
                    hour=hour,
                    weekday=weekday,
                )

        self.db_session.commit()

    def _ingest_sessions(self, degrees: list[Degree]) -> None:
        """Ingest session records from all class pages into the database.

        Iterates over every class page within the degree hierarchy. For each
        session, resolves its subject, teachers, classes, and rooms using
        cached database entries, then creates weekly session records spanning
        the page's date range. If a multi-class session already exists for the
        same week, weekday, time, and class, the existing session-class
        relation is updated to point at the correct subject instead of creating
        a duplicate.

        Args:
            degrees: Structured degree hierarchy with populated ``pages``.

        Raises:
            ValueError: If a referenced year, subject, teacher, class, or room
                cannot be found in the database.
        """
        session_dao = SessionDAO(self.db_session)
        class_red_block_dao = ClassRedBlockDAO(self.db_session)
        subject_dao = SubjectDAO(self.db_session)
        session_class_subject_dao = SessionClassSubjectDAO(self.db_session)

        for degree in degrees:
            for year in degree["years"]:
                year_key = (degree["acronym"], year["number"])
                year_db_entry = self.year_entries.get(year_key)
                if not year_db_entry:
                    raise ValueError(
                        f"Year {year['number']} not found for degree {degree['acronym']}",
                    )

        for degree in degrees:
            for year in degree["years"]:
                year_db_entry = self.year_entries[(degree["acronym"], year["number"])]

                for class_ in year["classes"]:
                    class_db_entry = self.class_entries.get(class_["code"])
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
                        subjects_by_acronym = {}
                        for subject in class_page["subjects"]:
                            subject_db_entry = self.subject_entries.get(subject["number"])
                            if subject_db_entry is None:
                                subject_db_entry = subject_dao.create(
                                    year_id=year_db_entry.id,
                                    number=subject["number"],
                                    code=subject["code"],
                                    acronym=subject["acronym"],
                                    name=subject["name"],
                                )
                                self.subject_entries[subject["number"]] = subject_db_entry

                            subjects_by_acronym[subject["acronym"]] = subject_db_entry

                        for scraped_session in class_page["sessions"]:
                            current_date = class_page["start_date"]
                            original_block_id = uuid.uuid7()

                            subject_db_entry = subjects_by_acronym.get(
                                scraped_session["subject_acronym"],
                            )
                            if not subject_db_entry:
                                raise ValueError(
                                    f"Subject acronym {scraped_session['subject_acronym']} not found for year {year['number']} of degree {degree['acronym']}",
                                )

                            teacher_ids = {
                                self.teacher_entries[teacher_number].id
                                for teacher_number in set(scraped_session["teachers"])
                            }
                            class_ids = {
                                self.class_entries[class_code].id
                                for class_code in set(scraped_session["classes"])
                            }
                            room_ids = (
                                set()
                                if "Online" in scraped_session["rooms"]
                                else {
                                    self.room_entries[room_name].id
                                    for room_name in set(scraped_session["rooms"])
                                }
                            )

                            while current_date <= class_page["end_date"]:
                                if len(class_ids) > 1:
                                    existing = session_dao.get_by_week_weekday_start_time_and_class(
                                        week=current_date,
                                        weekday=scraped_session["weekday"],
                                        start_time=scraped_session["start_time"],
                                        class_id=class_db_entry.id,
                                    )
                                    if existing is not None:
                                        session_class_subject_db_entry = (
                                            session_class_subject_dao.get_session_and_class(
                                                session_id=existing.id,
                                                class_id=class_db_entry.id,
                                            )
                                        )

                                        if session_class_subject_db_entry is not None:
                                            if (
                                                session_class_subject_db_entry.subject_id
                                                != subject_db_entry.id
                                            ):
                                                session_class_subject_db_entry.subject_id = (
                                                    subject_db_entry.id
                                                )
                                        else:
                                            raise ValueError(
                                                f"Relation session-class-subject not found for class {class_db_entry.code} with session at week: {current_date}, weekday: {scraped_session['weekday']}, starting hour: {scraped_session['start_time']}",
                                            )

                                        current_date += timedelta(weeks=1)
                                        continue

                                with self.db_session.begin_nested():
                                    session_entry_db = session_dao.create(
                                        week=current_date,
                                        weekday=scraped_session["weekday"],
                                        start_time=scraped_session["start_time"],
                                        duration=scraped_session["duration"],
                                        type_=("T" if scraped_session["is_theoretical"] else "TP"),
                                        original_block_id=original_block_id,
                                        teacher_ids=teacher_ids,
                                        room_ids=room_ids,
                                    )

                                    for class_id in class_ids:
                                        session_class_subject_dao.create(
                                            session_id=session_entry_db.id,
                                            class_id=class_id,
                                            subject_id=subject_db_entry.id,
                                        )

                                current_date += timedelta(weeks=1)

        self.db_session.commit()

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
        session_dao = SessionDAO(self.db_session)
        session_class_subject_dao = SessionClassSubjectDAO(self.db_session)

        subjects = self.subject_entries.values()
        visited_classes: set[Class] = set()

        for subject in subjects:
            shift = 1
            sessions_db_entries = session_dao.get_by_subject_type(subject, "T")

            for session_db_entry in sessions_db_entries:
                classes: set[Class] = {
                    session_class_subject.class_
                    for session_class_subject in session_class_subject_dao.get_by_session(
                        session_id=session_db_entry.id,
                    )
                }
                classes_no_shift: set[Class] = classes.difference(visited_classes)

                if len(classes_no_shift) == 0:
                    continue

                for class_ in classes_no_shift:
                    class_.shift = shift
                    visited_classes.add(class_)

                shift += 1

        self.db_session.commit()
