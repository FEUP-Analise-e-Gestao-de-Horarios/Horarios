import shutil
import sqlite3
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
from src.ingestion.schemas.programs import Program
from src.ingestion.schemas.rooms import RoomLinks
from src.ingestion.scraper import Scraper
from src.ingestion.utils import pre_insert_red_blocks
from src.parser.utils import (
    are_weeks_overlapped,
    max_date,
    min_date,
)
from src.projects.models import Project


class IngestionManager:
    def __init__(self, proj_id: int):
        self.proj_id = proj_id
        self.proj = Project.objects.get(pk=proj_id)

        self.path = Path(settings.PROJECTS_DB_PATH) / str(proj_id)
        self.conn = sqlite3.connect(self.path / "general_database.db")
        self.cursor: sqlite3.Cursor = self.conn.cursor()

        self.scraper = Scraper(self.proj.url)
        self.turnosMap: dict[str, dict[int, list[str]]] = {}

    def run(self) -> None:
        try:
            self._setup()

            pre_insert_red_blocks(self.cursor, self.conn)

            teacher_links, programs, rooms = self.scraper.read_menu()
            self._ingest_teachers(teacher_links)
            self._ingest_sections(programs)
            self._ingest_rooms(rooms)

            self._parse_turnos()
            self._fix_turmas_without_turnos()
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
        self.proj.started_ingestion_at = timezone.now()
        self.proj.finished_ingestion_at = None
        self.proj.failed_ingestion_at = None
        self.proj.save()

    def _teardown_success(self) -> None:
        shutil.copy2(
            self.path / "general_database.db",
            self.path / "initial_database.db",
        )
        self.proj.finished_ingestion_at = timezone.now()
        self.proj.save()
        self.conn.close()
        self.scraper.close()

    def _teardown_failure(self) -> None:
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
                                self._update_turnos_map(
                                    course_code,
                                    session["sections"],
                                )

                    self.conn.commit()

    def _ingest_rooms(self, rooms: list[RoomLinks]) -> None:
        for room in rooms:
            ingest_room(self.cursor, room)
            self.conn.commit()

            for link in room["links"]:
                for time, day in self.scraper.get_room_page(link):
                    ingest_room_red_blocks(self.cursor, room["name"], time, day)
            self.conn.commit()

    # -----------------------------------------------------------------------
    # TODO Check functions bellow
    # -----------------------------------------------------------------------

    def _update_turnos_map(self, cod_uc: str, turnos: list[str]) -> None:
        """Adds or updates the turno entry for a teorica aula in the turnosMap."""
        if cod_uc in self.turnosMap:
            if turnos not in self.turnosMap[cod_uc].values():
                numeroTurno = max(self.turnosMap[cod_uc].keys())
                self.turnosMap[cod_uc][numeroTurno + 1] = turnos
                dicionario = self.turnosMap[cod_uc]
                chaves_ordenadas = sorted(
                    dicionario,
                    key=lambda chave: dicionario[chave],
                )
                del self.turnosMap[cod_uc]
                self.turnosMap[cod_uc] = {}
                aux = 1
                for chave in chaves_ordenadas:
                    self.turnosMap[cod_uc][aux] = dicionario[chave]
                    aux += 1
        else:
            self.turnosMap[cod_uc] = {1: turnos}

    def _parse_turnos(self) -> None:
        """
        Inserts the found shifts into the database.

        Uses the information in the turnosMap structure to populate the
        corresponding shifts table in the database.
        """

        for uc in self.turnosMap:
            for number in self.turnosMap[uc]:
                for turno in self.turnosMap[uc][number]:
                    if isinstance(turno, list):
                        for turma in turno:
                            stmtS = """SELECT * FROM turno WHERE idTurma=? AND idUC=?"""
                            self.cursor.execute(stmtS, (turma, uc))
                            result = self.cursor.fetchall()
                            if len(result) == 0:
                                stmtT = (
                                    """INSERT INTO turno (numero, idTurma, idUC) VALUES (?, ?, ?)"""
                                )
                                self.cursor.execute(stmtT, (number, turma, uc))
                                self.conn.commit()
                    else:
                        stmtS = """SELECT * FROM turno WHERE idTurma=? AND idUC=?"""
                        self.cursor.execute(stmtS, (turno, uc))
                        result = self.cursor.fetchall()
                        if len(result) == 0:
                            stmtT = """INSERT INTO turno (numero, idTurma, idUC) VALUES (?, ?, ?)"""
                            self.cursor.execute(stmtT, (number, turno, uc))
                            self.conn.commit()

    def _fix_turmas_without_turnos(self) -> None:
        """
        Assigns a shift to classes that have no associated shift in the database.
        """

        query = """
            SELECT tu.idTurma, tu.idUC
            FROM turmaUC tu
            LEFT JOIN turno tn ON tu.idTurma = tn.idTurma
            WHERE tn.idTurma IS NULL
        """
        self.cursor.execute(query)
        missing_turmas = self.cursor.fetchall()

        for turma in missing_turmas:
            idTurma, idUC = turma
            query = """
                INSERT INTO turno (numero, idTurma, idUC)
                VALUES (0, ?, ?)
            """
            self.cursor.execute(query, (idTurma, idUC))
        self.conn.commit()

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
