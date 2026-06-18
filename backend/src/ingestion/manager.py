import shutil
import uuid
from collections import defaultdict
from datetime import date, timedelta
from uuid import UUID

from django.utils import timezone
from sqlalchemy import insert, select, text
from sqlalchemy.orm import selectinload

from src.ingestion.schemas.classes import ClassPage, Degree, Teacher
from src.ingestion.schemas.classes import Session as ScrapedSession
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
from src.projects.projects_db.models import (
    Class,
    ParallelBlockCandidate,
    Room,
    Session,
    SessionClassSubject,
    Subject,
    Year,
)
from src.projects.projects_db.models import Teacher as TeacherModel
from src.projects.projects_db.models._secondary_tables import session_rooms, session_teachers
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
        """Close the database session on context-manager exit."""
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
            # Block ids must be assigned before parallel-block detection,
            # which groups sessions by original_block_id.
            self._assign_block_ids()
            self._detect_parallel_block_candidates()

            # -- Snapshot general_db into init_db ----------------------------------
            # Force a WAL checkpoint so every committed row lands in the main DB
            # file before the snapshot copy. Without this, commits still sitting
            # in the .db-wal file (notably the parallel block candidates written
            # just above) would be missing from initial_database.db, since
            # shutil.copy2 only copies the main .db file.
            self.db_session.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
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

        Records the completion timestamp on the project and closes the
        HTTP session. The database snapshot is taken earlier in :meth:`run`.
        """
        self.proj.ingestion_finished_at = timezone.now()
        self.proj.save()
        self.scraper.close()

    def _teardown_failure(self) -> None:
        """Record a failed ingestion run and release resources.

        Sets the failure timestamp on the project and closes the HTTP session.
        The database session is closed by the context manager's ``__exit__``.
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

        teacher_dao = TeacherDAO(self.db_session, flush_on_create=False)
        teacher_red_block_dao = TeacherRedBlockDAO(self.db_session, flush_on_create=False)

        for teacher in teachers:
            teacher_entry = teacher_dao.create(
                number=teacher["code"],
                acronym=teacher["acronym"],
                name=teacher["name"],
            )
            self.teacher_entries[teacher["code"]] = teacher_entry
        self.db_session.flush()

        for teacher in teachers:
            teacher_entry = self.teacher_entries[teacher["code"]]
            for hour, weekday in teacher["red_blocks"]:
                teacher_red_block_dao.create(
                    teacher_id=teacher_entry.id,
                    hour=hour,
                    weekday=weekday,
                )

        self.db_session.commit()

    def _ingest_classes(self, degrees: list[Degree]) -> None:
        """Ingest degrees, years, and classes into the database.

        Inserts all degree records first, then creates year entries for each
        degree, and finally inserts class records for each year. Red blocks,
        subjects, and sessions are handled separately by :meth:`_ingest_sessions`.

        Args:
            degrees: Structured degree hierarchy as returned by
                ``Scraper.read_menu``.
        """

        degree_dao = DegreeDAO(self.db_session, flush_on_create=False)
        year_dao = YearDAO(self.db_session, flush_on_create=False)
        class_dao = ClassDAO(self.db_session, flush_on_create=False)

        degree_entries: dict[str, object] = {}
        for degree in degrees:
            degree_entries[degree["acronym"]] = degree_dao.create(
                acronym=degree["acronym"],
                name=degree["name"],
            )
        self.db_session.flush()

        for degree in degrees:
            degree_entry = degree_entries[degree["acronym"]]
            for year in degree["years"]:
                self.year_entries[(degree["acronym"], year["number"])] = year_dao.create(
                    degree_id=degree_entry.id,
                    number=year["number"],
                )
        self.db_session.flush()

        for degree in degrees:
            for year in degree["years"]:
                year_entry = self.year_entries[(degree["acronym"], year["number"])]
                for class_ in year["classes"]:
                    self.class_entries[class_["code"]] = class_dao.create(
                        year_id=year_entry.id,
                        code=class_["code"],
                        shift=0,
                    )

        self.db_session.commit()

    def _ingest_rooms(self, rooms: list[RoomInfo]) -> None:
        """Ingest room metadata and unavailability blocks into the database.

        For each room, inserts its record and then fetches a timetable page
        to collect and store its red blocks.

        Args:
            rooms: Room entries as returned by ``Scraper.read_menu``.
        """

        rooms_data = [(room, self.scraper.get_room_page(room["link"])) for room in rooms]

        room_dao = RoomDAO(self.db_session, flush_on_create=False)
        room_red_block_dao = RoomRedBlockDAO(self.db_session, flush_on_create=False)

        for room, _red_blocks in rooms_data:
            self.room_entries[room["name"]] = room_dao.create(
                name=room["name"],
                type=room["type_"],
                size=room["size"],
                seats=room["seats"],
            )
        self.db_session.flush()

        for room, red_blocks in rooms_data:
            room_entry = self.room_entries[room["name"]]
            for hour, weekday in red_blocks:
                room_red_block_dao.create(
                    room_id=room_entry.id,
                    hour=hour,
                    weekday=weekday,
                )

        self.db_session.commit()

    def _ingest_sessions(self, degrees: list[Degree]) -> None:
        """Ingest class red blocks, subjects, and session records into the database.

        For each class page, inserts red blocks (first page only, as they are
        week-invariant), resolves subjects, and builds weekly session records
        with their teacher/room/class-subject associations. All session data is
        collected in memory and bulk-inserted at the end for performance.

        When a multi-class session has already been created by another class in
        the same time slot, the existing record is reused and its class-subject
        mapping is updated instead of creating a duplicate.

        Args:
            degrees: Structured degree hierarchy with populated ``pages``.

        Raises:
            ValueError: If a referenced year, subject, teacher, class, or room
                cannot be found in the database.
        """
        class_red_block_dao = ClassRedBlockDAO(self.db_session, flush_on_create=False)
        subject_dao = SubjectDAO(self.db_session, flush_on_create=False)

        # -- Validate that all years were previously ingested -----------------
        for degree in degrees:
            for year in degree["years"]:
                year_key = (degree["acronym"], year["number"])
                if year_key not in self.year_entries:
                    raise ValueError(
                        f"Year {year['number']} not found for degree {degree['acronym']}",
                    )

        # -- Pending rows to bulk-insert at the end ---------------------------
        pending_sessions: list[dict] = []
        pending_session_teachers: list[dict] = []
        pending_session_rooms: list[dict] = []

        # Maps (session_id, class_id) -> subject_id for class-subject links
        class_subject_map: dict[tuple[UUID, UUID], UUID] = {}
        # Index for duplicate detection: (week, weekday, start_time, class_id) -> session_id
        session_lookup: dict[tuple[date, int, int, UUID], UUID] = {}

        # -- Process each class across all degrees ----------------------------
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

                    # Red blocks are week-invariant, only insert from first page
                    for hour, weekday in first_class_page["red_blocks"]:
                        class_red_block_dao.create(
                            class_id=class_db_entry.id,
                            hour=hour,
                            weekday=weekday,
                        )

                    for class_page in class_["pages"]:
                        subjects_by_acronym = self._resolve_page_subjects(
                            class_page,
                            year_db_entry,
                            subject_dao,
                        )
                        weeks = self._compute_weeks(class_page)

                        for scraped_session in class_page["sessions"]:
                            self._process_scraped_session(
                                scraped_session=scraped_session,
                                weeks=weeks,
                                subjects_by_acronym=subjects_by_acronym,
                                class_db_entry=class_db_entry,
                                degree_acronym=degree["acronym"],
                                year_number=year["number"],
                                pending_sessions=pending_sessions,
                                pending_session_teachers=pending_session_teachers,
                                pending_session_rooms=pending_session_rooms,
                                class_subject_map=class_subject_map,
                                session_lookup=session_lookup,
                            )

        # -- Bulk insert and commit -------------------------------------------
        self._bulk_insert_session_data(
            pending_sessions,
            pending_session_teachers,
            pending_session_rooms,
            class_subject_map,
        )
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

    def _detect_parallel_block_candidates(self) -> None:
        """Detect and persist candidate parallel block groups.

        Finds sessions that share ``(week, weekday, start_time, subject_id)``
        in their first week of occurrence and groups their parent blocks
        (``original_block_id``) together. Groups are stored in
        ``parallel_block_candidates`` for later user review.

        Only groups with at least two distinct blocks are persisted. Each
        persisted group is identified by a fresh ``uuid.uuid7()`` label.
        """
        detection_sql = text("""
            WITH session_subjects AS (
                SELECT DISTINCT
                    s.original_block_id,
                    MIN(s.week) OVER (PARTITION BY s.original_block_id) AS first_week,
                    s.weekday,
                    s.start_time,
                    scs.subject_id
                FROM sessions s
                JOIN sessions_classes_subject scs ON scs.session_id = s.id
            ),
            session_groups AS (
                SELECT
                    original_block_id,
                    DENSE_RANK() OVER (ORDER BY first_week, weekday, start_time, subject_id) AS group_id,
                    COUNT(*) OVER (PARTITION BY first_week, weekday, start_time, subject_id) AS group_size
                FROM session_subjects
            )
            SELECT DISTINCT group_id, original_block_id
            FROM session_groups
            WHERE group_size > 1
            ORDER BY group_id, original_block_id
        """)

        rows = self.db_session.execute(detection_sql).all()

        # Bucket blocks by raw group id.
        # Raw SQL bypasses SQLAlchemy's UUID coercion, so each value comes back
        # as the underlying 32-char hex string from sqlite.
        raw_groups: defaultdict[int, set[UUID]] = defaultdict(set)
        for raw_group_id, original_block_id in rows:
            raw_groups[raw_group_id].add(UUID(original_block_id))

        # Assign each group a fresh UUID label.
        candidate_groups: dict[UUID, set[UUID]] = {
            uuid.uuid7(): block_ids for block_ids in raw_groups.values()
        }

        candidate_rows = [
            {"candidate_group_id": group_id, "original_block_id": block_id}
            for group_id, block_ids in candidate_groups.items()
            for block_id in block_ids
        ]
        if candidate_rows:
            self.db_session.execute(insert(ParallelBlockCandidate), candidate_rows)

        self.db_session.commit()

    def _assign_block_ids(self) -> None:
        """Regroup sessions into blocks by fingerprinting their content.

        The scraper splits each class's schedule into multiple pages by date
        range, so a single recurring session that spans a page boundary is
        ingested as several disjoint per-page blocks. This post-processing
        step discards those provisional ids and reassigns ``original_block_id``
        purely by content: all sessions that share an identical fingerprint
        are collapsed into a single block identified by a fresh
        ``uuid.uuid7()``, regardless of which weeks they fall in (the weeks
        need not be contiguous).

        A fingerprint covers everything that identifies a session except the
        week it falls in (see :meth:`_session_fingerprint`). Two sessions in
        the same week must therefore not share a fingerprint: they could not
        belong to the same block under the ``(week, original_block_id)``
        unique constraint.

        Raises:
            ValueError: If two sessions in the same week share a fingerprint.
        """
        sessions = self.db_session.scalars(
            select(Session).options(
                selectinload(Session.teachers),
                selectinload(Session.rooms),
                selectinload(Session.session_class_subjects),
            ),
        ).all()

        # Bucket every session by its week-invariant content fingerprint.
        sessions_by_fingerprint: defaultdict[tuple[object, ...], list[Session]] = defaultdict(
            list,
        )
        for session in sessions:
            sessions_by_fingerprint[self._session_fingerprint(session)].append(session)

        # Each fingerprint is one block, spanning every week it occurs in.
        for group in sessions_by_fingerprint.values():
            block_id = uuid.uuid7()
            sessions_by_week: dict[date, Session] = {}
            for session in group:
                clash = sessions_by_week.get(session.week)
                if clash is not None:
                    raise ValueError(
                        f"Sessions {clash.id} and {session.id} share a "
                        f"content fingerprint in week {session.week} and "
                        f"cannot belong to the same block",
                    )
                sessions_by_week[session.week] = session
                session.original_block_id = block_id

        self.db_session.commit()

    # -----------------------------------------------------------------------
    # Auxiliar functions
    # -----------------------------------------------------------------------

    def _resolve_page_subjects(
        self,
        class_page: ClassPage,
        year_db_entry: Year,
        subject_dao: SubjectDAO,
    ) -> dict[str, Subject]:
        """Resolve or create subject DB entries for a single class page.

        Uses the instance-level ``subject_entries`` cache to avoid duplicates
        across pages. New subjects are flushed so their IDs are available.

        Returns:
            Mapping of subject acronym to its DB entry.
        """
        subjects_by_acronym: dict[str, Subject] = {}
        for subject in class_page["subjects"]:
            subject_db_entry = self.subject_entries.get(subject["number"])
            if subject_db_entry is None:
                subject_db_entry = subject_dao.create(
                    year=year_db_entry,
                    number=subject["number"],
                    code=subject["code"],
                    acronym=subject["acronym"],
                    name=subject["name"],
                )
                self.subject_entries[subject["number"]] = subject_db_entry
            elif year_db_entry not in subject_db_entry.years:
                # Same UC taught in another year (e.g. shared/optional): record
                # the extra year membership rather than overwriting the first.
                subject_db_entry.years.append(year_db_entry)
            subjects_by_acronym[subject["acronym"]] = subject_db_entry
        self.db_session.flush()
        return subjects_by_acronym

    @staticmethod
    def _compute_weeks(class_page: ClassPage) -> list[date]:
        """Return all weekly start dates covered by a class page's date range."""
        weeks: list[date] = []
        current = class_page["start_date"]
        while current <= class_page["end_date"]:
            weeks.append(current)
            current += timedelta(weeks=1)
        return weeks

    @staticmethod
    def _session_fingerprint(session: Session) -> tuple[object, ...]:
        """Return a hashable, week-invariant fingerprint of a session's content.

        Two sessions in different weeks belong to the same recurring block iff
        their fingerprints are equal: same weekday, start time, duration and
        type, the same teacher and room id sets, and the same set of
        (class id, subject id) pairs. The pairs are fingerprinted together
        rather than as two independent sets so that sessions mapping distinct
        subjects to distinct classes cannot collide.
        """
        return (
            session.weekday,
            session.start_time,
            session.duration,
            session.type,
            tuple(sorted(teacher.id for teacher in session.teachers)),
            tuple(sorted(room.id for room in session.rooms)),
            tuple(
                sorted((scs.class_id, scs.subject_id) for scs in session.session_class_subjects),
            ),
        )

    def _process_scraped_session(
        self,
        scraped_session: ScrapedSession,
        weeks: list[date],
        subjects_by_acronym: dict[str, Subject],
        class_db_entry: Class,
        degree_acronym: str,
        year_number: int,
        pending_sessions: list[dict],
        pending_session_teachers: list[dict],
        pending_session_rooms: list[dict],
        class_subject_map: dict[tuple[UUID, UUID], UUID],
        session_lookup: dict[tuple[date, int, int, UUID], UUID],
    ) -> None:
        """Build weekly session rows for one scraped session block.

        For each week in the page's date range, either creates a new session
        record or, for multi-class sessions that were already created by
        another class, updates the existing class-subject mapping.
        """
        # Provisional id; _assign_block_ids reassigns block ids post-ingestion.
        original_block_id = uuid.uuid7()

        subject_db_entry = subjects_by_acronym.get(
            scraped_session["subject_acronym"],
        )
        if not subject_db_entry:
            raise ValueError(
                f"Subject acronym {scraped_session['subject_acronym']} "
                f"not found for year {year_number} of degree {degree_acronym}",
            )

        teacher_ids, class_ids, room_ids = self._resolve_session_references(
            scraped_session,
        )

        for week in weeks:
            # -- Multi-class duplicate detection: reuse session already created by another class
            if len(class_ids) > 1:
                lookup_key = (
                    week,
                    scraped_session["weekday"],
                    scraped_session["start_time"],
                    class_db_entry.id,
                )
                existing_session_id = session_lookup.get(lookup_key)

                if existing_session_id is not None:
                    scs_key = (existing_session_id, class_db_entry.id)
                    if scs_key in class_subject_map:
                        if class_subject_map[scs_key] != subject_db_entry.id:
                            class_subject_map[scs_key] = subject_db_entry.id
                    else:
                        raise ValueError(
                            f"Relation session-class-subject not found for "
                            f"class {class_db_entry.code} with session at "
                            f"week: {week}, weekday: {scraped_session['weekday']}, "
                            f"starting hour: {scraped_session['start_time']}",
                        )
                    continue

            # -- Create new session record
            session_id = uuid.uuid7()

            pending_sessions.append(
                {
                    "id": session_id,
                    "week": week,
                    "weekday": scraped_session["weekday"],
                    "start_time": scraped_session["start_time"],
                    "duration": scraped_session["duration"],
                    "type": scraped_session["type"],
                    "original_block_id": original_block_id,
                },
            )

            for teacher_id in teacher_ids:
                pending_session_teachers.append(
                    {
                        "session_id": session_id,
                        "teacher_id": teacher_id,
                    },
                )

            for room_id in room_ids:
                pending_session_rooms.append(
                    {
                        "session_id": session_id,
                        "room_id": room_id,
                    },
                )

            # Register class-subject links and update duplicate detection index
            for class_id in class_ids:
                class_subject_map[(session_id, class_id)] = subject_db_entry.id
                session_lookup[
                    (week, scraped_session["weekday"], scraped_session["start_time"], class_id)
                ] = session_id

    def _resolve_session_references(
        self,
        scraped_session: ScrapedSession,
    ) -> tuple[set[UUID], set[UUID], set[UUID]]:
        """Look up teacher, class, and room DB IDs for a scraped session.

        Returns:
            ``(teacher_ids, class_ids, room_ids)`` resolved from cached entries.
        """
        teacher_ids = {self.teacher_entries[code].id for code in set(scraped_session["teachers"])}
        class_ids = {self.class_entries[code].id for code in set(scraped_session["classes"])}
        room_ids = (
            set()
            if "Online" in scraped_session["rooms"]
            else {self.room_entries[name].id for name in set(scraped_session["rooms"])}
        )
        return teacher_ids, class_ids, room_ids

    def _bulk_insert_session_data(
        self,
        pending_sessions: list[dict],
        pending_session_teachers: list[dict],
        pending_session_rooms: list[dict],
        class_subject_map: dict[tuple[UUID, UUID], UUID],
    ) -> None:
        """Execute bulk inserts for all collected session data."""
        if pending_sessions:
            self.db_session.execute(insert(Session), pending_sessions)
        if pending_session_teachers:
            self.db_session.execute(
                session_teachers.insert(),
                pending_session_teachers,
            )
        if pending_session_rooms:
            self.db_session.execute(
                session_rooms.insert(),
                pending_session_rooms,
            )
        if class_subject_map:
            self.db_session.execute(
                insert(SessionClassSubject),
                [
                    {"session_id": sid, "class_id": cid, "subject_id": sub_id}
                    for (sid, cid), sub_id in class_subject_map.items()
                ],
            )
