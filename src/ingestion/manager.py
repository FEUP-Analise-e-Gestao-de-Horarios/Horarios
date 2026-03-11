import shutil
import sqlite3
from collections import defaultdict
from pathlib import Path

from django.conf import settings
from django.utils import timezone

from src.ingestion.ingestors.rooms import ingest_room, ingest_room_red_blocks
from src.ingestion.ingestors.sections import (
    ingest_course,
    ingest_program,
    ingest_section,
    ingest_section_red_blocks,
    ingest_session,
)
from src.ingestion.ingestors.teachers import ingest_teacher, ingest_teacher_red_blocks
from src.ingestion.schemas.misc import TurnosMap
from src.ingestion.schemas.rooms import RoomLinks
from src.ingestion.schemas.sections import Program
from src.ingestion.scraper import Scraper
from src.ingestion.utils import pre_insert_red_blocks
from src.parser.utils import (
    are_weeks_overlapped,
    max_date,
    min_date,
)
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
        the project's URL, and initializes an empty shift map used during
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
        self.course_shifts_map: TurnosMap = defaultdict(
            lambda: defaultdict(lambda: defaultdict(dict)),
        )

    def run(self) -> None:
        """Execute the full ingestion pipeline.

        Runs setup, pre-populates the red-blocks table, scrapes and ingests
        teachers, sections, and rooms, then runs post-processing steps. On
        success, calls ``_teardown_success``; on any exception, calls
        ``_teardown_failure`` and re-raises.
        """
        try:
            self._setup()

            pre_insert_red_blocks(self.cursor, self.conn)

            teacher_links, programs, rooms = self.scraper.read_menu()
            self._ingest_teachers(teacher_links)
            self._ingest_sections(programs)
            self._ingest_rooms(rooms)
            self._ingest_course_shifts()

            self._fix_sections_without_shifts()
            self._cleanup_aulas()
            self._aulas_simultaneas()

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

    def _ingest_sections(self, programs: list[Program]) -> None:
        """Ingest programs, sections, courses, and sessions into the database.

        First inserts all programs, then for each section fetches all weekly
        schedule pages, inserts red blocks (from the first page only, as they
        are week-invariant), and inserts courses and sessions from every page.
        Theoretical sessions are also recorded in the internal shift map for
        later processing.

        Args:
            programs: Structured program hierarchy as returned by
                ``Scraper.read_menu``.

        Raises:
            ValueError: If a section has no schedule pages.
        """
        for program in programs:
            ingest_program(self.cursor, program)
        self.conn.commit()

        for program in programs:
            for year in program["years"]:
                for section in year["sections"]:
                    ingest_section(
                        self.cursor,
                        program["acronym"],
                        year["number"],
                        section["code"],
                    )
                    self.conn.commit()

                    section_pages = [
                        self.scraper.get_section_page(link) for link in section["links"]
                    ]
                    if not section_pages:
                        raise ValueError(
                            f"No pages found for section {section['code']}",
                        )

                    # A class's red blocks only need to be parsed once,
                    # since they don't change between weeks
                    for time, day in section_pages[0]["red_blocks"]:
                        ingest_section_red_blocks(
                            self.cursor,
                            section["code"],
                            time,
                            day,
                        )
                    self.conn.commit()

                    for section_page in section_pages:
                        for course in section_page["courses"]:
                            ingest_course(self.cursor, course, program["acronym"])
                        self.conn.commit()

                        courses_by_acronym = {s["acronym"]: s for s in section_page["courses"]}
                        for session in section_page["sessions"]:
                            course_code = courses_by_acronym[session["course_acronym"]]["code"]

                            ingest_session(
                                self.cursor,
                                course_code,
                                session,
                                section_page["start_date"],
                                section_page["end_date"],
                            )

                            if session["is_theoretical"]:
                                self._update_course_shifts_map(
                                    program["acronym"],
                                    year["number"],
                                    course_code,
                                    session["sections"],
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

    def _ingest_course_shifts(self) -> None:
        """Inserts all recorded course shifts into the ``turno`` table.

        Iterates over :attr:`course_shifts_map` and inserts each
        (shift number, section, course) triple, skipping entries that already
        exist. A single commit is issued at the end.
        """
        for program in self.course_shifts_map:
            for year in self.course_shifts_map[program]:
                for course in self.course_shifts_map[program][year]:
                    for turno_number in self.course_shifts_map[program][year][course]:
                        for section in self.course_shifts_map[program][year][course][turno_number]:
                            self.cursor.execute(
                                "SELECT * FROM turno WHERE idTurma=? AND idUC=?",
                                (section, course),
                            )
                            result = self.cursor.fetchall()
                            if len(result) == 0:
                                self.cursor.execute(
                                    "INSERT INTO turno (numero, idTurma, idUC) VALUES (?, ?, ?)",
                                    (turno_number, section, course),
                                )
        self.conn.commit()

    # -----------------------------------------------------------------------
    # Course shift management
    # -----------------------------------------------------------------------

    def _update_course_shifts_map(
        self,
        program: str,
        year: int,
        course_code: str,
        sections: list[str],
    ) -> None:
        """Records a new shift for a course, keeping shifts sorted by their smallest section code.

        If ``sections`` is already registered for this course, this is a no-op.
        Otherwise, adds it and re-numbers all shifts from 1 in ascending order
        of each shift's minimum section code.

        Args:
            program: Acronym of the program the course belongs to.
            year: Academic year number within the program.
            course_code: Institutional code of the course.
            sections: Section codes that form the new shift.
        """
        course_map = self.course_shifts_map[program][year][course_code]

        if sections not in course_map.values():
            all_sections = sorted(
                [*course_map.values(), sections],
                key=min,
            )
            course_map.clear()
            for i, sections in enumerate(all_sections, 1):
                course_map[i] = sections

    def _fix_sections_without_shifts(self) -> None:
        stmt = """
            SELECT tu.idTurma, tu.idUC
            FROM turmaUC tu
            LEFT JOIN turno tn ON tu.idTurma = tn.idTurma
            WHERE tn.idTurma IS NULL
        """
        self.cursor.execute(stmt)
        missing_sections = self.cursor.fetchall()

        for section in missing_sections:
            print(section)
            section_id, course_id = section
            stmt = """
                INSERT INTO turno (numero, idTurma, idUC)
                VALUES (0, ?, ?)
            """
            self.cursor.execute(stmt, (section_id, course_id))
        self.conn.commit()

    # -----------------------------------------------------------------------
    # TODO Check functions bellow
    # -----------------------------------------------------------------------

    def _cleanup_aulas(self) -> None:
        """
        Deduplicates and merges overlapping lessons in the database.
        """
        stmtAulas = """SELECT DISTINCT diaSemana, horaInicial, duracao, teorico, idDocente, idUC, idTurma
                        FROM aula
                        JOIN aulaDocente ON aula.id = aulaDocente.idAula
                        JOIN aulaUC ON aula.id = aulaUC.idAula
                        JOIN aulaTurmas ON aula.id = aulaTurmas.idAula"""
        self.cursor.execute(stmtAulas)
        aulas = self.cursor.fetchall()

        for aula in aulas:
            dia, hora, duracao, isTeorica, docente, uc, turma = aula
            stmtTest = """SELECT * FROM aula
                          JOIN aulaDocente ON aula.id = aulaDocente.idAula
                          JOIN aulaUC ON aula.id = aulaUC.idAula
                          JOIN aulaTurmas ON aula.id = aulaTurmas.idAula
                          WHERE diaSemana=? AND horaInicial=? AND duracao=? AND teorico=? AND idDocente=? AND idUC=? AND idTurma=?"""
            self.cursor.execute(
                stmtTest,
                (dia, hora, duracao, isTeorica, docente, uc, turma),
            )
            results = self.cursor.fetchall()

            while len(results) > 1 and any(
                are_weeks_overlapped(
                    results[i][5],
                    results[i][6],
                    results[j][5],
                    results[j][6],
                )
                for i in range(len(results))
                for j in range(i + 1, len(results))
            ):
                results.sort(key=lambda x: x[5])
                idAula1, si1, sf1 = results[0][0], results[0][5], results[0][6]
                idAula2, si2, sf2 = results[1][0], results[1][5], results[1][6]
                if are_weeks_overlapped(si1, sf1, si2, sf2):
                    ssi = min_date(si1, si2)
                    ssf = max_date(sf1, sf2)
                    results_list = list(results[0])
                    results_list[5] = ssi
                    results_list[6] = ssf
                    results[0] = tuple(results_list)
                    stmtUpdate = """UPDATE aula SET semanaInicial=?, semanaFinal=? WHERE id=?"""
                    self.cursor.execute(stmtUpdate, (ssi, ssf, idAula1))
                    for table in ["aulaDocente", "aulaUC", "aulaSala", "aulaTurmas"]:
                        self.cursor.execute(
                            f"DELETE FROM {table} WHERE idAula=?",
                            (idAula2,),
                        )
                    self.cursor.execute("DELETE FROM aula WHERE id=?", (idAula2,))
                    results.pop(1)
                    continue
                results.pop(0)
        self.conn.commit()

    def _aulas_simultaneas(self) -> None:
        """
        Finds simultaneous lessons in the schedule and inserts the information into the database.

        Queries the database to find simultaneous lessons from different courses.
        Simultaneous lessons share the same: lecturer, room, day, and time. There is
        also an overlap in the weeks they occur. However, the course and the UC must
        be different. Once found, the lessons are inserted into an appropriate table
        in the database.
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
        aulas_sim = self.cursor.fetchall()

        for entry in aulas_sim:
            idAula1, idAula2, idCurso1, idCurso2 = entry
            query = """
                INSERT into aulasSimultaneas (aula1, aula2, curso1, curso2)
                VALUES (?, ?, ?, ?)
            """
            self.cursor.execute(query, (idAula1, idAula2, idCurso1, idCurso2))

        self.conn.commit()
