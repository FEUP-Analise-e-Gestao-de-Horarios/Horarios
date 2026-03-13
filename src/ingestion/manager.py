import shutil
import sqlite3
from collections import defaultdict
from datetime import date
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from src.ingestion.ingestors.rooms import ingest_room, ingest_room_red_blocks
from src.ingestion.ingestors.sections import (
    ingest_class,
    ingest_classred_blocks,
    ingest_degree,
    ingest_session,
    ingest_subject,
)
from src.ingestion.ingestors.teachers import ingest_teacher, ingest_teacher_red_blocks
from src.ingestion.schemas.misc import TurnosMap
from src.ingestion.schemas.rooms import RoomLinks
from src.ingestion.schemas.sections import Degree
from src.ingestion.scraper import Scraper
from src.ingestion.utils import check_date_range_overlap, pre_insert_red_blocks
from src.projects.models import Project


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

            pre_insert_red_blocks(self.cursor, self.conn)

            teacher_links, degrees, rooms = self.scraper.read_menu()
            self._ingest_teachers(teacher_links)
            self._ingest_classes(degrees)
            self._ingest_rooms(rooms)
            self._ingest_subject_shifts()

            self._fix_classes_without_shifts()
            self._cleanup_sessions()
            self._find_simultaneous_classes()

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
        for link in teacher_links:
            teacher_page = self.scraper.get_teacher_page(link)

            ingest_teacher(self.cursor, teacher_page)
            self.conn.commit()

            for time, day in teacher_page["red_blocks"]:
                ingest_teacher_red_blocks(self.cursor, teacher_page["code"], time, day)
            self.conn.commit()

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
        for degree in degrees:
            ingest_degree(self.cursor, degree)
        self.conn.commit()

        for degree in degrees:
            for year in degree["years"]:
                for class_ in year["classes"]:
                    ingest_class(
                        self.cursor,
                        degree["acronym"],
                        year["number"],
                        class_["code"],
                    )
                    self.conn.commit()

                    class_pages = [self.scraper.get_class_page(link) for link in class_["links"]]
                    if not class_pages:
                        raise ValueError(
                            f"No pages found for class {class_['code']}",
                        )

                    # A class's red blocks only need to be parsed once,
                    # since they don't change between weeks
                    for time, day in class_pages[0]["red_blocks"]:
                        ingest_classred_blocks(
                            self.cursor,
                            class_["code"],
                            time,
                            day,
                        )
                    self.conn.commit()

                    for class_page in class_pages:
                        for subject in class_page["subjects"]:
                            ingest_subject(self.cursor, subject, degree["acronym"])
                        self.conn.commit()

                        subjects_by_acronym = {s["acronym"]: s for s in class_page["subjects"]}
                        for session in class_page["sessions"]:
                            subject_code = subjects_by_acronym[session["subject_acronym"]]["code"]

                            ingest_session(
                                self.cursor,
                                subject_code,
                                session,
                                class_page["start_date"],
                                class_page["end_date"],
                            )

                            if session["is_theoretical"]:
                                self._update_subject_shifts_map(
                                    degree["acronym"],
                                    year["number"],
                                    subject_code,
                                    session["classes"],
                                )

                    self.conn.commit()

    def _ingest_rooms(self, rooms: list[RoomLinks]) -> None:
        """Ingest room metadata and unavailability blocks into the database.

        For each room, inserts its record and then fetches every timetable
        page to collect and store its red blocks.

        Args:
            rooms: Room entries as returned by ``Scraper.read_menu``.
        """
        for room in rooms:
            ingest_room(self.cursor, room)
            self.conn.commit()

            for link in room["links"]:
                for time, day in self.scraper.get_room_page(link):
                    ingest_room_red_blocks(self.cursor, room["name"], time, day)
            self.conn.commit()

    def _ingest_subject_shifts(self) -> None:
        """Inserts all recorded subject shifts into the ``turno`` table.

        Iterates over :attr:`subject_shifts_map` and inserts each
        (shift number, class, subject) triple, skipping entries that already
        exist. A single commit is issued at the end.
        """
        for degree in self.subject_shifts_map:
            for year in self.subject_shifts_map[degree]:
                for subject in self.subject_shifts_map[degree][year]:
                    for turno_number in self.subject_shifts_map[degree][year][subject]:
                        for class_ in self.subject_shifts_map[degree][year][subject][turno_number]:
                            self.cursor.execute(
                                "SELECT * FROM turno WHERE idTurma=? AND idUC=?",
                                (class_, subject),
                            )
                            result = self.cursor.fetchall()
                            if len(result) == 0:
                                self.cursor.execute(
                                    "INSERT INTO turno (numero, idTurma, idUC) VALUES (?, ?, ?)",
                                    (turno_number, class_, subject),
                                )
        self.conn.commit()

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

    def _fix_classes_without_shifts(self) -> None:
        """Insert a placeholder shift (number 0) for classes that have no shift assigned.

        Queries for all (class, subject) pairs in ``turmaUC`` that have no
        corresponding row in ``turno``, then inserts a row with shift number 0
        for each. This ensures every class-subject association has at least one
        shift record, preventing referential gaps in downstream queries.
        """
        stmt = """
            SELECT tu.idTurma, tu.idUC
            FROM turmaUC tu
            LEFT JOIN turno tn ON tu.idTurma = tn.idTurma
            WHERE tn.idTurma IS NULL
        """
        self.cursor.execute(stmt)
        missing_classes = self.cursor.fetchall()

        for class_ in missing_classes:
            class_id, subject_id = class_
            stmt = """
                INSERT INTO turno (numero, idTurma, idUC)
                VALUES (0, ?, ?)
            """
            self.cursor.execute(stmt, (class_id, subject_id))
        self.conn.commit()

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
