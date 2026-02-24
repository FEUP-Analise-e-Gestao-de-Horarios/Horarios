import re
import shutil
import sqlite3
from collections import defaultdict
from datetime import datetime
from typing import Any

import requests
from bs4 import BeautifulSoup

from core.models import Project

from .db import (
    insert_aula,
    insert_cursos,
    insert_turma,
    insert_ucs,
    pre_inserir_blocos_vermelhos,
)
from .directories import createDir
from .models import Aula
from .utils import (
    are_weeks_overlapped,
    get_dia_from_index,
    get_index,
    max_date,
    min_date,
    table_to_matrix,
)

# Algumas tipologias encontradas
# 14 - O, 15 - OT, 16 - Pratica, 17 - PL, 18 - S
# 19 - Teorica, 20 - TC, 21 - Teorico-Pratica
# Não existe tipologia para além da 21
tipologias = ["td_tipologia_" + str(id) for id in range(1, 22)]


class Parser:
    def __init__(self, paginas: str, user_pk: str, name: str):
        self.paginas = paginas
        self.user_pk = user_pk
        self.name = name
        self.turnosMap: dict[str, dict[int, list[str]]] = {}
        self.conn: sqlite3.Connection | None = None
        self.cursor: sqlite3.Cursor | None = None
        self.proj = None
        self.proj_id: int | None = None
        self.path: str | None = None

    def run(self) -> None:
        """
        Função executora do parse.

        Cria a entrada do projeto na base de dados, a diretoria do projeto,
        e a ligação à base de dados. Chama as funções de parse para preencher
        a base de dados. No final, copia o conteúdo da general_database para
        a initial_database, e marca o projeto como parsed. Em caso de falha,
        a base de dados é eliminada e a diretoria é removida.
        """
        try:
            self._setup()

            req = requests.get(self.paginas)
            soup = BeautifulSoup(req.content, "html.parser")

            links = soup.find("frame", {"name": "links"})
            src = links["src"]

            req = requests.get(self.paginas + src)
            menu = BeautifulSoup(req.content, "html.parser").find("ul", {"id": "menu"})

            print("Project Started")
            pre_inserir_blocos_vermelhos(self.cursor, self.conn)

            self._parse_docentes(menu.findChildren(recursive=False)[0])
            self._parse_turmas(menu.findChildren(recursive=False)[1])
            self._parse_salas(menu.findChildren(recursive=False)[2])
            self._parse_turnos()
            self._fix_turmas_without_turnos()
            self._cleanup_aulas()
            self._aulas_simultaneas()

            self._teardown_success()
            print("Project Parsed")

        except Exception:
            self._teardown_failure()
            raise

    # -----------------------------------------------------------------------
    # Setup / teardown
    # -----------------------------------------------------------------------

    def _setup(self) -> None:
        self.path, self.proj_id = createDir(self.user_pk, self.name)
        assert self.path is not None
        self.proj = Project.objects.get(project=self.name)
        self.conn = sqlite3.connect(
            self.path + "/general_database.db", check_same_thread=False
        )
        self.cursor = self.conn.cursor()

    def _teardown_success(self) -> None:
        shutil.copy2(
            self.path + "/general_database.db", self.path + "/initial_database.db"
        )
        self.proj.isParsed = True
        self.proj.save()
        self.conn.close()

    def _teardown_failure(self) -> None:
        if self.proj is not None:
            self.proj.delete()
        if self.conn is not None:
            self.conn.close()
        if self.proj_id is not None:
            shutil.rmtree("./database/Project" + str(self.proj_id), ignore_errors=True)

    # -----------------------------------------------------------------------
    # Funções de parse
    # -----------------------------------------------------------------------

    def _parse_horario_vermelhos(self, req: Any) -> list[int]:
        """
        Recebe uma página e devolve uma lista dos IDs de blocos vermelhos presentes.

        Realiza o parse dos blocos vermelhos num horário. O horário pode ser de
        turma, docente, sala ou UC. Devolve uma lista que contém os IDs de todos
        os blocos vermelhos encontrados, de acordo com a tabela de blocos vermelhos
        na base de dados.
        """

        soup = BeautifulSoup(req.content, "html.parser")

        # Obtém todos os elementos de bloco vermelho no horário
        vermelhos = soup.find_all("td", {"class": "td_vermelha"})

        # Se não existirem blocos vermelhos, devolve a lista vazia
        if len(vermelhos) == 0:
            return []

        redBlockList = []
        table = soup.find("center").find("table", {"class": "tabela_principal"})
        matrix = table_to_matrix(table)

        days = vermelhos[0].parent.parent.findChildren(recursive=False)[3]
        daySpans = {}

        for i, day in enumerate(days.findChildren()):
            if i == 0:
                continue
            daySpans[day.text] = day.get("colspan")

        for item in vermelhos:
            parent = item.parent
            index, matrix = get_index(item, matrix)

            time = int(parent.findChild().text.replace(":", ""))
            day = get_dia_from_index(index, daySpans)

            stmt = """SELECT id FROM blocosVermelhos WHERE hora=? AND diaSemana=?"""
            result = self.cursor.execute(stmt, (time, day)).fetchone()

            redBlockList.append(result[0])

        return redBlockList

    def _parse_horario(
        self,
        req: requests.Response,
        curso_or_uc: str,
        parsingTurma: bool,
        lista_de_aulas: set[Aula],
    ) -> None:
        """
        Realiza o parse do horário completo de uma página.

        Recebe uma página e realiza o parse do horário. A página pode ser de UC
        ou de turma (indicado pelo booleano parsingTurma). Todas as aulas
        encontradas são transformadas em objetos Aula e colocados num set, para
        garantir que não há ocorrências duplicadas.
        """

        soup = BeautifulSoup(req.content, "html.parser")

        aulaBlocks = soup.find("center").find_all("td", {"class": tipologias})

        # Parse de semana de início e fim deste horário
        semanas = soup.find("td", {"class": "cabtitulo"}).contents
        semanas = str(semanas[-1])
        semanaIniEFim = semanas.split("Semanas: ")[1]
        semanaIni, _, semanaFim = semanaIniEFim.partition(" - ")
        if not semanaFim:
            semanaFim = semanaIni

        si_obj = datetime.strptime(semanaIni, "%d/%m/%Y")
        sf_obj = datetime.strptime(semanaFim, "%d/%m/%Y")

        semanaIni = si_obj.strftime("%Y-%m-%d")
        semanaFim = sf_obj.strftime("%Y-%m-%d")

        # Parse de todas as UCs do horário (uma turma)
        if parsingTurma:
            ucs = self._parse_ucs(req)
            insert_ucs(ucs, curso_or_uc, self.cursor)
            self.conn.commit()

        # Parse e construção de uma tabela de docentes da turma
        docentes_table = soup.findAll("table")[3].findAll("tr")[2:]
        docentes_table = list(map(str, docentes_table))

        docentes_temp = defaultdict(list)

        for item in docentes_table:
            parts = item.split('<td align="left" valign="middle">')
            abrevs = parts[2].split("</td>")[0]
            codes = parts[3].split("</td>")[0]
            docentes_temp[abrevs].append(codes)

        # Parse das colunas dos dias de aulas
        dias = aulaBlocks[0].parent.parent.findChildren(recursive=False)[3]
        diaSpans = {}
        for i, dia in enumerate(dias.findChildren()):
            if i == 0:
                continue
            diaSpans[dia.text] = dia.get("colspan")

        # Criação de matriz a partir do horário
        table = soup.find("center").find("table", {"class": "tabela_principal"})
        matrix = table_to_matrix(table)

        for aulaBlock in aulaBlocks:
            count = 0
            aula = {}
            aula["isTeorica"] = aulaBlock.get("class")[0] == "td_tipologia_19"
            aula["span"] = aulaBlock.get("rowspan")
            pattern = r"\[(.*?)\]"
            matches = re.findall(pattern, aulaBlock.text)
            aula["salas"] = matches[2] if len(matches) > 2 else "Online"
            aula["turmas"] = matches[0].split("; ")

            docentes_aulaBlock = (
                matches[1].replace("(", "").replace(")", "").split("; ")
            )

            aula["semanaIni"] = semanaIni
            aula["semanaFim"] = semanaFim

            lista_docentes = []
            for i in docentes_aulaBlock:
                if len(docentes_temp[i]) == 1:
                    lista_docentes.append(docentes_temp[i][0])
                else:
                    lista_docentes.append(docentes_temp[i][count])
                    count += 1

            aula["docentes"] = lista_docentes

            # Adição de turnos da UC ao mapa de turnos
            sigla = aulaBlock.contents[0]
            cod_uc = curso_or_uc if not parsingTurma else ucs[sigla][0]
            if aula["isTeorica"]:
                turnos = aula["turmas"]
                if cod_uc in self.turnosMap:
                    if turnos not in self.turnosMap[cod_uc].values():
                        numeroTurno = max(self.turnosMap[cod_uc].keys())
                        self.turnosMap[cod_uc][numeroTurno + 1] = turnos
                        dicionario = self.turnosMap[cod_uc]
                        chaves_ordenadas = sorted(
                            dicionario, key=lambda chave: dicionario[chave]
                        )
                        del self.turnosMap[cod_uc]
                        self.turnosMap[cod_uc] = {}
                        aux = 1
                        for chave in chaves_ordenadas:
                            self.turnosMap[cod_uc][aux] = dicionario[chave]
                            aux += 1
                else:
                    self.turnosMap[cod_uc] = {1: turnos}

            # Parse de dia e hora da aulaBlock
            pai = aulaBlock.parent
            aula["hora"] = int(pai.findChild().text.replace(":", ""))
            index, matrix = get_index(aulaBlock, matrix)

            aula["dia"] = get_dia_from_index(index, diaSpans)
            aula["cod_uc"] = cod_uc

            aula_obj = Aula(aula)
            lista_de_aulas.add(aula_obj)

    def _parse_docentes(self, docentes: Any) -> None:
        """
        Realiza o parse de todo o menu de docentes.

        Realiza o parse do menu de docentes, visitando cada uma das páginas
        individuais. Obtém os dados relevantes de cada docente, incluindo
        os seus blocos vermelhos.
        """

        children = docentes.find("ul").findChildren(recursive=False)
        for child in children:
            content = child.find("ul").find_all("li", recursive=False)
            k = 0
            for i in content:
                a = i.find("a", recursive=False)
                link = a["href"]
                req = requests.get(self.paginas + link)

                if k == 0:
                    web_s = req.content
                    soup = BeautifulSoup(web_s, "html.parser")
                    content = soup.find("td", {"class": "cabtitulo"}).contents
                    content = str(content)
                    if '"' in content:
                        first = content.split('"')[1]
                        sigla = content.split("<br/>, '")[1].split("'")[0]
                        if sigla in first:
                            nome = first[len(sigla) :]
                        else:
                            nome = ""
                        codigo = content.split("<br/>, '")[2].split("'")[0]
                    else:
                        content = content.split("', <br/>, '")
                        sigla = content[1].split("'")[0]
                        if sigla in content[0]:
                            nome = content[0][len(sigla) + 2 :]
                        else:
                            nome = ""
                        codigo = content[2].split("'")[0]
                    if " - " in nome:
                        nome = nome[3:]
                    if nome == "":
                        nome = sigla
                    nome = re.sub(r"[^\w\s]", "", nome)
                    k = 1

                vermelhos = self._parse_horario_vermelhos(req)
                for idBlocoVermelho in vermelhos:
                    stmtT = """INSERT OR IGNORE INTO blocoDocente (idBloco, idDocente) VALUES (?, ?)"""
                    self.cursor.execute(stmtT, (idBlocoVermelho, codigo))
                    self.conn.commit()

            stmt = """INSERT INTO docentes (numeroMecanografico, nome, abreviacao) VALUES (?, ?, ?)"""
            self.cursor.execute(
                stmt,
                (
                    codigo,
                    nome,
                    sigla,
                ),
            )
            self.conn.commit()

    def _parse_cursos(self, cursos: Any) -> set[tuple[str, str]]:
        """
        Realiza o parse do menu de cursos.

        Realiza o parse do menu de cursos, obtendo a informação relevante.
        Os tuplos (nome, abreviatura) são colocados num set para garantir que
        não há duplicados. Devolve o set de tuplos.
        """

        allCursos = set()

        for curso in cursos:
            info = curso.find("a").contents
            abreviatura = info[0].split(" - ")[0]
            nome = info[0].split(" - ", 1)[1]
            allCursos.add((nome, abreviatura))

        return allCursos

    def _parse_turmas(self, menu_turmas: Any) -> None:
        """
        Realiza o parse do menu de turmas.

        Realiza o parse de todas as turmas, visitando cada horário individual.
        Obtém todas as aulas de cada horário, inserindo a informação relevante
        na base de dados.
        """

        children = menu_turmas.find("ul").findChildren(recursive=False)

        cursos = self._parse_cursos(children)
        insert_cursos(cursos, self.cursor)

        for child in children:
            idCurso = child.find("a").contents
            idCurso = idCurso[0].split(" - ")[0]
            anos = child.find("ul").findChildren(recursive=False)

            for ano in anos:
                numeroAno = ano.find("a").contents
                numeroStr = numeroAno[0]
                numeroStr = numeroStr.split(" ")[1]
                plano_turmas = ano.find("ul").find("li")
                turmas = plano_turmas.find("ul").findChildren(recursive=False)

                lista_de_aulas = set()

                for turma in turmas:
                    codigo = turma.find("a").contents
                    codigo = str(codigo).split("'")[1]
                    semanasLi = turma.find("ul").find_all("li")

                    insert_turma(idCurso, numeroStr, codigo, self.cursor)
                    self.conn.commit()

                    parsed_vermelhos = False

                    for semana in semanasLi:
                        a = semana.find("a", recursive=False)

                        link = a["href"]
                        req = requests.get(self.paginas + link)

                        self._parse_horario(req, idCurso, True, lista_de_aulas)

                        # Os blocos vermelhos de uma turma só precisam de ser
                        # parsed uma vez, já que não mudam entre semanas
                        if not parsed_vermelhos:
                            vermelhos = self._parse_horario_vermelhos(req)
                            for idBlocoVermelho in vermelhos:
                                stmt = """INSERT OR IGNORE INTO blocoTurma (idBloco, idTurma) VALUES (?, ?)"""
                                self.cursor.execute(stmt, (idBlocoVermelho, codigo))
                                self.conn.commit()
                            parsed_vermelhos = True

                for aula in lista_de_aulas:
                    insert_aula(aula, self.cursor)

                lista_de_aulas = set()

        self.conn.commit()

    def _parse_ucs(self, req: requests.Response) -> dict[str, list[str, str, str]]:
        """
        Realiza o parse de UCs na página de cada turma.

        Recebe uma página de horário de uma turma e realiza o parse de todas
        as UCs presentes. Devolve um dicionário com entradas indexadas pela
        sigla da UC.
        """

        soup = BeautifulSoup(req.content, "html.parser")

        table = [str(row) for row in soup.findAll("table")[4].findAll("tr")[2:]]

        ucs = {}
        for row in table:
            row_items = row.split('<td align="left" valign="middle">')[1:]
            (codigo_nome, sigla, numero_uc) = (
                item.split("</td>")[0] for item in row_items
            )
            (codigo, nome) = codigo_nome.split(" - ", 1)

            ucs[sigla] = [codigo, nome, numero_uc]
        return ucs

    def _parse_salas(self, salas: Any) -> None:
        """
        Realiza o parse das salas a partir do menu lateral.

        Recebe o elemento do menu correspondente às salas e realiza o parse de
        cada uma, guardando os elementos relevantes, incluindo os blocos
        vermelhos.
        """

        children = salas.find("ul").findChildren(recursive=False)
        for child in children:
            a_list = child.find_all("a", {"class": "timetable-link"})
            content = child.find("a").contents
            if "__cf_email__" in str(content):
                content = ["EaD"]
            sala = str(content).split("'")[1]
            with open("parser/Salas.txt") as file:
                alreadyInserted = False
                for line in file:
                    if sala in line:
                        alreadyInserted = True
                        tipo, capacidade = (
                            line.strip().split(" - ")[0],
                            line.strip().split(" - ")[-1],
                        )
                        if tipo == "Anf":
                            if "." in capacidade:
                                capacidade = capacidade[-2:]
                            tamanhoComp = "N/A"
                        elif tipo == "PCs":
                            if capacidade == "Grandes":
                                tamanhoComp = "> 21"
                            elif capacidade == "Media20":
                                capacidade = "Media"
                                tamanhoComp = "20"
                            elif capacidade == "Media16":
                                capacidade = "Media"
                                tamanhoComp = "16"
                            else:
                                tamanhoComp = "< 15"
                        else:
                            tamanhoComp = "N/A"
                        stmt = """INSERT INTO salas(numero, tipo, capacidade, tamanhoComp) VALUES (?, ?, ?, ?)"""
                        self.cursor.execute(
                            stmt,
                            (
                                sala,
                                tipo,
                                capacidade,
                                tamanhoComp,
                            ),
                        )
                        self.conn.commit()

                if not alreadyInserted:
                    stmt = """INSERT INTO salas(numero, tipo, capacidade, tamanhoComp) VALUES (?, ?, ?, ?)"""
                    self.cursor.execute(
                        stmt,
                        (
                            sala,
                            "Desconhecido",
                            "Desconhecido",
                            "Desconhecido",
                        ),
                    )
                    self.conn.commit()

            for a in a_list:
                link = a.get("href")
                req = requests.get(self.paginas + link)
                vermelhos = self._parse_horario_vermelhos(req)
                for idBlocoVermelho in vermelhos:
                    stmtT = """INSERT OR IGNORE INTO salaBloco (idBloco, idSala) VALUES (?, ?)"""
                    self.cursor.execute(stmtT, (idBlocoVermelho, sala))
                    self.conn.commit()

    def _parse_turnos(self) -> None:
        """
        Insere os turnos encontrados na base de dados.

        Usa a informação na estrutura turnosMap para preencher a tabela
        correspondente aos turnos na base de dados.
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
                                stmtT = """INSERT INTO turno (numero, idTurma, idUC) VALUES (?, ?, ?)"""
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
        Atribui um turno às turmas que não têm um turno associado na base de dados.
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
        Deduplica e funde aulas sobrepostas na base de dados.
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
                stmtTest, (dia, hora, duracao, isTeorica, docente, uc, turma)
            )
            results = self.cursor.fetchall()

            while len(results) > 1 and any(
                are_weeks_overlapped(
                    results[i][5], results[i][6], results[j][5], results[j][6]
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
                    stmtUpdate = (
                        """UPDATE aula SET semanaInicial=?, semanaFinal=? WHERE id=?"""
                    )
                    self.cursor.execute(stmtUpdate, (ssi, ssf, idAula1))
                    for table in ["aulaDocente", "aulaUC", "aulaSala", "aulaTurmas"]:
                        self.cursor.execute(
                            f"DELETE FROM {table} WHERE idAula=?", (idAula2,)
                        )
                    self.cursor.execute("DELETE FROM aula WHERE id=?", (idAula2,))
                    results.pop(1)
                    continue
                results.pop(0)
        self.conn.commit()

    def _aulas_simultaneas(self) -> None:
        """
        Encontra aulas simultâneas no horário e insere a informação na base de dados.

        Realiza uma query à base de dados para encontrar aulas simultâneas de
        cursos diferentes. Aulas simultâneas têm os mesmos: docente, sala, dia, e
        hora. Há também uma sobreposição nas semanas em que ocorrem. No entanto,
        o curso e a UC têm de ser diferentes. Depois de encontradas as aulas, são
        inseridas numa tabela apropriada na base de dados.
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
