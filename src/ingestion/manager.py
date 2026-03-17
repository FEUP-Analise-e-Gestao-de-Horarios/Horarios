import shutil
import sqlite3
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from uuid import UUID

from django.conf import settings
from django.utils import timezone

from src.ingestion.schemas.classes import Degree
from src.ingestion.schemas.misc import TurnosMap
from src.ingestion.schemas.rooms import RoomLinks
from src.ingestion.scraper import Scraper
from src.ingestion.utils import check_date_range_overlap
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
            self._ingest_teachers(teacher_links)
            self._ingest_classes(degrees)
            self._ingest_rooms(rooms)
            self._ingest_sessions(degrees)
            self._ingest_shifts()

            # self._fix_classes_without_shifts()
            # self._cleanup_sessions()
            # self._find_simultaneous_classes()

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

    def _ingest_teachers(self, teacher_links: list[str]) -> None:
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
        teacher_pages = [self.scraper.get_teacher_page(link) for link in teacher_links]

        with get_session(general_db(self.proj_id)) as session:
            teacher_dao = TeacherDAO(session)
            teacher_red_block_dao = TeacherRedBlockDAO(session)
            for teacher_page in teacher_pages:
                teacher = teacher_dao.create(
                    number=teacher_page["code"],
                    acronym=teacher_page["acronym"],
                    name=teacher_page["name"],
                )

                for red_block in teacher_page["red_blocks"]:
                    teacher_red_block_dao.create(
                        teacher_id=teacher.id,
                        hour=red_block[0],
                        weekday=red_block[1],
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
            class_red_block_dao = ClassRedBlockDAO(session_db)
            subject_dao = SubjectDAO(session_db)

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

                        class_pages = self.scraper.get_class_pages(class_)

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

    def _ingest_sessions(self, degrees: list[Degree]) -> None:
        with get_session(general_db(self.proj_id)) as session_db:
            session_dao = SessionDAO(session_db)
            teacher_dao = TeacherDAO(session_db)
            subject_dao = SubjectDAO(session_db)
            class_dao = ClassDAO(session_db)

            for degree in degrees:
                for year in degree["years"]:
                    for class_ in year["classes"]:
                        for class_page in class_["class_pages"]:
                            # add teachers without redblocks
                            for teacher_page in class_page["teachers"]:
                                if teacher_dao.get_by_number(teacher_page["code"]) is None:
                                    teacher_page = teacher_dao.create(
                                        number=teacher_page["code"],
                                        acronym=teacher_page["acronym"],
                                        name=teacher_page["name"],
                                    )
                            subjects_by_acronym = {s["acronym"]: s for s in class_page["subjects"]}

                            for session in class_page["sessions"]:
                                subject_code = subjects_by_acronym[session["subject_acronym"]][
                                    "code"
                                ]

                                subject = subject_dao.get_by_code(subject_code)

                                if subject is None:
                                    raise ValueError(
                                        f"No subject with the code {subject_code} was found",
                                    )

                                teachers_id: list[UUID] = [
                                    t.id
                                    for number in session["teachers"]
                                    if (t := teacher_dao.get_by_number(number)) is not None
                                ]

                                assert len(teachers_id) == len(
                                    session["teachers"],
                                ), (
                                    f"One or more teachers were not found in {subjects_by_acronym[session['subject_acronym']]['name']} subject"
                                )

                                classes_id = [
                                    c.id
                                    for code in session["classes"]
                                    if (c := class_dao.get_by_code(code)) is not None
                                ]

                                assert len(classes_id) == len(
                                    session["classes"],
                                ), (
                                    f"One or more classes were not found in {subjects_by_acronym[session['subject_acronym']]['name']} subject"
                                )

                                current_date = class_page["start_date"]
                                class_obj = class_dao.get_by_code(class_["code"])

                                rooms = session["room"] if session["room"][0] != "Online" else None

                                assert class_obj is not None, (
                                    f"Class with code {class_['code']} was not found"
                                )

                                while current_date <= class_page["end_date"]:
                                    if (
                                        session_dao.get_by_class_with_attributes(
                                            week=current_date,
                                            weekday=session["weekday"],
                                            start_time=session["start_time"],
                                            duration=session["duration"],
                                            type=("T" if session["is_theoretical"] else "TP"),
                                            class_id=class_obj.id,
                                        )
                                        is None
                                    ):
                                        session_dao.create(
                                            week=current_date,
                                            weekday=session["weekday"],
                                            start_time=session["start_time"],
                                            duration=session["duration"],
                                            type=("T" if session["is_theoretical"] else "TP"),
                                            room_names=rooms,
                                            class_ids=classes_id,
                                            teacher_ids=teachers_id,
                                            subject_ids=[subject.id],
                                        )
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

    # -----------------------------------------------------------------------
    # Subject <-> shift management
    # -----------------------------------------------------------------------

    def _update_subject_shifts_map(
        self,
        degree: str,
        year: int,
        subject_code: str,
        classes: list[str],
    ) -> None:
        """Records a new shift for a subject, keeping shifts sorted by their smallest class code.

        If ``classes`` is already registered for this subject, this is a no-op.
        Otherwise, adds it and re-numbers all shifts from 1 in ascending order
        of each shift's minimum class code.

        Args:
            degree: Acronym of the degree the subject belongs to.
            year: Academic year number within the degree.
            subject_code: Institutional code of the subject.
            classes: Class codes that form the new shift.
        """
        subject_map = self.subject_shifts_map[degree][year][subject_code]

        if classes not in subject_map.values():
            all_classes = sorted(
                [*subject_map.values(), classes],
                key=min,
            )
            subject_map.clear()
            for i, classes in enumerate(all_classes, 1):
                subject_map[i] = classes

    # -----------------------------------------------------------------------
    # Post processing
    # -----------------------------------------------------------------------

    def _cleanup_sessions(self) -> None:
        """Merge duplicate session records that share the same schedule and overlap in date range.

        Sessions are considered duplicates if they have identical schedule attributes
        (day, time, duration, type, teacher, subject unit, and class). When
        duplicates with overlapping week ranges are found, they are merged into a single
        record spanning the union of their date ranges, and the redundant record is deleted
        (along with its associated rows in aulaDocente, aulaUC, aulaSala, and aulaTurmas).

        The loop processes pairs in ascending date order and repeats until no overlapping
        duplicates remain for a given session signature.
        """
        stmt = """
            SELECT DISTINCT diaSemana, horaInicial, duracao, teorico, idDocente, idUC, idTurma
            FROM aula
            JOIN aulaDocente ON aula.id = aulaDocente.idAula
            JOIN aulaUC ON aula.id = aulaUC.idAula
            JOIN aulaTurmas ON aula.id = aulaTurmas.idAula
        """
        self.cursor.execute(stmt)
        sessions = self.cursor.fetchall()

        for session in sessions:
            dia, hora, duracao, isTeorica, docente, uc, turma = session
            stmt = """
                SELECT * FROM aula
                JOIN aulaDocente ON aula.id = aulaDocente.idAula
                JOIN aulaUC ON aula.id = aulaUC.idAula
                JOIN aulaTurmas ON aula.id = aulaTurmas.idAula
                WHERE diaSemana=? AND horaInicial=? AND duracao=? AND teorico=? AND idDocente=? AND idUC=? AND idTurma=?
            """
            self.cursor.execute(
                stmt,
                (dia, hora, duracao, isTeorica, docente, uc, turma),
            )
            results = [
                (*r[:5], date.fromisoformat(r[5]), date.fromisoformat(r[6]), *r[7:])
                for r in self.cursor.fetchall()
            ]

            while len(results) > 1 and any(
                check_date_range_overlap(
                    (results[i][5], results[i][6]),
                    (results[j][5], results[j][6]),
                )
                for i in range(len(results))
                for j in range(i + 1, len(results))
            ):
                results.sort(key=lambda x: x[5])
                session_id_1, range_start_1, range_end_1 = (
                    results[0][0],
                    results[0][5],
                    results[0][6],
                )
                session_id_2, range_start_2, range_end_2 = (
                    results[1][0],
                    results[1][5],
                    results[1][6],
                )
                if check_date_range_overlap(
                    (range_start_1, range_end_1),
                    (range_start_2, range_end_2),
                ):
                    min_range_start = min(range_start_1, range_start_2)
                    max_range_end = max(range_end_1, range_end_2)
                    results_list = list(results[0])
                    results_list[5] = min_range_start
                    results_list[6] = max_range_end
                    results[0] = tuple(results_list)
                    self.cursor.execute(
                        "UPDATE aula SET semanaInicial=?, semanaFinal=? WHERE id=?",
                        (min_range_start, max_range_end, session_id_1),
                    )
                    for table in ["aulaDocente", "aulaUC", "aulaSala", "aulaTurmas"]:
                        self.cursor.execute(
                            f"DELETE FROM {table} WHERE idAula=?",
                            (session_id_2,),
                        )
                    self.cursor.execute("DELETE FROM aula WHERE id=?", (session_id_2,))
                    results.pop(1)
                    continue
                results.pop(0)
        self.conn.commit()

    def _find_simultaneous_classes(self) -> None:
        """
        Finds simultaneous lessons across different subjects and records them in the database.

        Queries for pairs of lessons that share the same lecturer, room, day, start time,
        and overlapping week ranges, but belong to different subjects. Each such pair is
        inserted into the `aulasSimultaneas` table. Pairs are deduplicated so (A, B) and
        (B, A) are never stored as separate entries.
        """
        query = """
            SELECT DISTINCT
                CASE WHEN a1.id < a2.id THEN a1.id ELSE a2.id END AS id_aula1,
                CASE WHEN a1.id < a2.id THEN a2.id ELSE a1.id END AS id_aula2,
                uc1.idCurso AS id_curso1,
                uc2.idCurso AS id_curso2
            FROM aula AS a1
            JOIN aulaSala AS asala1 ON a1.id = asala1.idAula
            JOIN aulaDocente AS ad1 ON a1.id = ad1.idAula
            JOIN aulaUC AS auc1 ON a1.id = auc1.idAula
            JOIN uc AS uc1 ON auc1.idUC = uc1.codigo
            JOIN aula AS a2
            JOIN aulaSala AS asala2 ON a2.id = asala2.idAula
            JOIN aulaDocente AS ad2 ON a2.id = ad2.idAula
            JOIN aulaUC AS auc2 ON a2.id = auc2.idAula
            JOIN uc AS uc2 ON auc2.idUC = uc2.codigo
            WHERE a2.id > a1.id
                AND ad1.idDocente = ad2.idDocente
                AND asala1.idSala = asala2.idSala
                AND a1.diaSemana = a2.diaSemana
                AND a1.horaInicial = a2.horaInicial
                AND (
                    (a1.semanaInicial <= a2.semanaFinal AND a1.semanaFinal >= a2.semanaInicial)
                    OR
                    (a1.semanaInicial >= a2.semanaInicial AND a1.semanaFinal <= a2.semanaFinal)
                    OR
                    (a1.semanaInicial <= a2.semanaInicial AND a1.semanaFinal >= a2.semanaFinal)
                )
                AND uc1.idCurso <> uc2.idCurso;
        """
        self.cursor.execute(query)
        simultaneous_sessions = self.cursor.fetchall()

        for entry in simultaneous_sessions:
            idAula1, idAula2, idCurso1, idCurso2 = entry
            query = """
                INSERT into aulasSimultaneas (aula1, aula2, curso1, curso2)
                VALUES (?, ?, ?, ?)
            """
            self.cursor.execute(query, (idAula1, idAula2, idCurso1, idCurso2))

        self.conn.commit()
