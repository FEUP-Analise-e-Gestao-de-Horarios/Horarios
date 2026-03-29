import json
import os
import sqlite3
from pathlib import Path

from src.FeupScheduleEditor.models import AulaChange, AulaInfo

from . import models


def converter_horario(num):
    hora, minuto = divmod(num, 100)
    return f"{hora:02d}:{minuto:02d}"


def calculate_hora_final(horaInicial, duracao):
    # Remove the colon from the horaInicial string
    horaInicial = horaInicial.replace(":", "")

    # Convert the horaInicial to hours and minutes
    hours = int(horaInicial[:2])
    minutes = int(horaInicial[2:])

    # Calculate the total minutes based on duracao
    total_minutes = hours * 60 + minutes + duracao * 30

    # Calculate the final hours and minutes
    final_hours = total_minutes // 60
    final_minutes = total_minutes % 60

    # Format the horaFinal as an integer in the HHMM format
    horaFinal = int(f"{final_hours:02d}{final_minutes:02d}")

    return horaFinal


def get_primary_key(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    for column in columns:
        if column[5]:
            return column[1]
    return None


def addChangeToDict(changesDict, table_name, primaryKey, diff_data1, diff_data2):
    # print("Table: ", table_name)
    # print("Primary Key: ", primaryKey)

    new_changes = [dict(row) for row in diff_data1]
    prev_changes = [dict(row) for row in diff_data2]

    for prev in prev_changes:
        for new in new_changes:
            if prev[primaryKey] == new[primaryKey]:
                changesDict[len(changesDict) + 1] = (table_name, prev, new)
                break


def handleAulas(setFinal, setInicial, ProjectNumber):
    path = "Project" + str(ProjectNumber)
    connIni = sqlite3.connect(
        "./databases/" + path + "/initial_database.db",
        check_same_thread=False,
    )
    connIni.row_factory = sqlite3.Row
    cursorIni = connIni.cursor()
    allChanges = []
    diff1 = setFinal - setInicial
    diff2 = setInicial - setFinal
    listaInicial = []
    listaFinal = []
    for elem in diff1:
        listaInicial.append(elem)
    for elem2 in diff2:
        listaFinal.append(elem2)
    listaInicial = []
    listaFinal = []
    dicInicial = {}
    dicFinal = {}

    for k in diff1:
        for index in range(0, 4):
            listaInicial.append(k[index])
    for k in diff2:
        for index in range(0, 4):
            listaFinal.append(k[index])

    for i, item in enumerate(listaInicial):
        if i % 4 == 0:
            key = item
            values = tuple(listaInicial[i + 1 : i + 4])
            dicFinal[key] = values
    for i, item in enumerate(listaFinal):
        if i % 4 == 0:
            key = item
            values = tuple(listaFinal[i + 1 : i + 4])
            dicInicial[key] = values

    # CHECK IF THERE ARE TRADES

    for key in dicInicial:
        if key in dicFinal:
            stmtB = """SELECT * FROM aulaUC WHERE idAula=?"""
            cursorIni.execute(stmtB, (key,))
            resultAulaUC = cursorIni.fetchone()
            stmtTurma = """SELECT * FROM aulaTurmas WHERE idAula=?"""
            cursorIni.execute(stmtTurma, (key,))
            resultTurma = cursorIni.fetchone()
            horaFinalInicial = converter_horario(
                calculate_hora_final(
                    converter_horario(dicInicial[key][0]),
                    dicInicial[key][1],
                ),
            )
            horaFinalFinal = converter_horario(
                calculate_hora_final(
                    converter_horario(dicFinal[key][0]),
                    dicFinal[key][1],
                ),
            )
            change = globalNaturalLanguage(
                "horario",
                resultAulaUC["idUc"],
                dicInicial[key][2],
                dicFinal[key][2],
                converter_horario(dicInicial[key][0]),
                converter_horario(dicFinal[key][0]),
                "",
                "",
                "",
                "",
                resultTurma["idTurma"],
                "",
                "",
                key,
                horaFinalInicial,
                horaFinalFinal,
            )
            allChanges.append(change)
    return allChanges


def handleSalas(setFinal, setInicial, ProjectNumber):  # TESTED AND WORKING
    allChanges = []
    diff1 = setFinal - setInicial
    lista1 = []
    diff2 = setInicial - setFinal
    lista2 = []
    for elem in diff1:
        lista1.append(elem)
    for elem2 in diff2:
        lista2.append(elem2)
    for newSala in lista1:
        change = globalNaturalLanguage(
            "salasAdd",
            "",
            "",
            "",
            "",
            "",
            newSala["numero"],
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
        )
        allChanges.append(change)
    for delSala in lista2:
        change = globalNaturalLanguage(
            "salasRem",
            "",
            "",
            "",
            "",
            "",
            delSala["numero"],
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
        )
        allChanges.append(change)
    return allChanges


def handleDocentes(setFinal, setInicial, ProjectNumber):  # TESTED AND WORKING
    allChanges = []
    diff1 = setFinal - setInicial
    lista1 = []
    diff2 = setInicial - setFinal
    lista2 = []
    for elem in diff1:
        lista1.append(elem)
    for elem2 in diff2:
        lista2.append(elem2)
    for newDocente in lista1:
        change = globalNaturalLanguage(
            "createDocente",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            newDocente["numeroMecanografico"],
            "",
            "",
            newDocente["nome"],
            newDocente["abreviacao"],
            "",
            "",
            "",
        )
        allChanges.append(change)
    for delDocente in lista2:
        change = globalNaturalLanguage(
            "removeDocente",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            delDocente["numeroMecanografico"],
            "",
            "",
            delDocente["nome"],
            delDocente["abreviacao"],
            "",
            "",
            "",
        )
        allChanges.append(change)
    return allChanges


def handleAulaDocente(setFinal, setInicial, ProjectNumber):  # TESTED AND WORKING
    path = "Project" + str(ProjectNumber)
    connIni = sqlite3.connect(
        "./databases/" + path + "/initial_database.db",
        check_same_thread=False,
    )
    connIni.row_factory = sqlite3.Row
    cursorIni = connIni.cursor()
    connFin = sqlite3.connect(
        "./databases/" + path + "/general_database.db",
        check_same_thread=False,
    )
    connFin.row_factory = sqlite3.Row
    cursorFin = connFin.cursor()
    allChanges = []
    diff1 = setFinal - setInicial
    diff2 = setInicial - setFinal

    listaInicial = []
    listaFinal = []
    dicInicial = {}
    dicFinal = {}

    for k in diff1:
        for index in range(0, len(k)):
            listaInicial.append(k[index])

    for k in diff2:
        for index in range(0, len(k)):
            listaFinal.append(k[index])

    for index in range(0, len(listaInicial) - 1, 2):
        # print("Index: ", index)
        key = listaInicial[index]
        value = listaInicial[index + 1]
        if key in dicFinal:
            dicFinal[key].append(value)
        else:
            dicFinal[key] = [value]
    for index2 in range(0, len(listaFinal) - 1, 2):
        key = listaFinal[index2]
        value = listaFinal[index2 + 1]
        if key in dicInicial:
            dicInicial[key].append(value)
        else:
            dicInicial[key] = [value]

    # CHECK IF THERE ARE TRADES

    for key in dicInicial:
        for elem in dicInicial[key]:
            stmt = """SELECT * FROM aula WHERE id=?"""
            cursorFin.execute(stmt, (key,))
            resultAula = cursorFin.fetchone()
            stmtB = """SELECT * FROM aulaUC WHERE idAula=?"""
            cursorIni.execute(stmtB, (key,))
            resultAulaUC = cursorIni.fetchone()
            stmtTurma = """SELECT * FROM aulaTurmas WHERE idAula=?"""
            cursorIni.execute(stmtTurma, (key,))
            resultTurma = cursorIni.fetchone()
            stmtDocente = """SELECT * FROM docentes WHERE numeroMecanografico=?"""
            cursorIni.execute(stmtDocente, (elem,))
            lastDocente = cursorIni.fetchone()
            change = globalNaturalLanguage(
                "docentesRem",
                resultAulaUC["idUC"],
                resultAula["diaSemana"],
                "",
                converter_horario(resultAula["horaInicial"]),
                "",
                "",
                "",
                lastDocente["abreviacao"],
                "",
                resultTurma["idTurma"],
                "",
                "",
                key,
                "",
                "",
            )
            allChanges.append(change)
    for key in dicFinal:
        for elem in dicFinal[key]:
            stmt = """SELECT * FROM aula WHERE id=?"""
            cursorFin.execute(stmt, (key,))
            resultAula = cursorFin.fetchone()
            stmtB = """SELECT * FROM aulaUC WHERE idAula=?"""
            cursorFin.execute(stmtB, (key,))
            resultAulaUC = cursorFin.fetchone()
            stmtTurma = """SELECT * FROM aulaTurmas WHERE idAula=?"""
            cursorFin.execute(stmtTurma, (key,))
            resultTurma = cursorFin.fetchone()
            stmtDocente = """SELECT * FROM docentes WHERE numeroMecanografico=?"""
            cursorFin.execute(stmtDocente, (elem,))
            firstDocente = cursorFin.fetchone()
            change = globalNaturalLanguage(
                "docentesAdd",
                resultAulaUC["idUC"],
                resultAula["diaSemana"],
                "",
                converter_horario(resultAula["horaInicial"]),
                "",
                "",
                "",
                firstDocente["abreviacao"],
                "",
                resultTurma["idTurma"],
                "",
                "",
                key,
                "",
                "",
            )
            allChanges.append(change)
    return allChanges


def handleAulaUC(setFinal, setInicial, ProjectNumber):  # TESTED AND WORKING
    path = "Project" + str(ProjectNumber)
    connIni = sqlite3.connect(
        "./databases/" + path + "/initial_database.db",
        check_same_thread=False,
    )
    connIni.row_factory = sqlite3.Row
    cursorIni = connIni.cursor()
    connFin = sqlite3.connect(
        "./databases/" + path + "/general_database.db",
        check_same_thread=False,
    )
    connFin.row_factory = sqlite3.Row
    cursorFin = connFin.cursor()
    allChanges = []
    diff1 = setFinal - setInicial
    diff2 = setInicial - setFinal

    listaInicial = []
    listaFinal = []
    dicInicial = {}
    dicFinal = {}

    for k in diff1:
        for index in range(0, len(k)):
            listaInicial.append(k[index])

    for k in diff2:
        for index in range(0, len(k)):
            listaFinal.append(k[index])

    for index in range(0, len(listaInicial) - 1, 2):
        # print("Index: ", index)
        key = listaInicial[index]
        value = listaInicial[index + 1]
        if key in dicFinal:
            dicFinal[key].append(value)
        else:
            dicFinal[key] = [value]
    for index2 in range(0, len(listaFinal) - 1, 2):
        key = listaFinal[index2]
        value = listaFinal[index2 + 1]
        if key in dicInicial:
            dicInicial[key].append(value)
        else:
            dicInicial[key] = [value]

    # CHECK IF THERE ARE TRADES
    print(f"ALL CHANGES GOING INTO UC: DicFinal: {dicFinal}, DicInicial: {dicInicial}")

    for key in dicInicial:
        for elem1, elem2 in enumerate(dicInicial[key]):
            stmt = """SELECT * FROM aula WHERE id=?"""
            cursorFin.execute(stmt, (key,))
            resultAula = cursorFin.fetchone()
            stmtTurma = """SELECT * FROM aulaTurmas WHERE idAula=?"""
            cursorIni.execute(stmtTurma, (key,))
            resultTurma = cursorIni.fetchone()
            change = globalNaturalLanguage(
                "uc",
                elem1,
                resultAula["diaSemana"],
                "",
                converter_horario(resultAula["horaInicial"]),
                "",
                "",
                "",
                "",
                elem2,
                resultTurma["idTurma"],
                "",
                "",
                key,
                "",
                "",
            )
            allChanges.append(change)
    return allChanges


def handleAulaTurmas(setFinal, setInicial, ProjectNumber):  # TESTED AND WORKING
    path = "Project" + str(ProjectNumber)
    connIni = sqlite3.connect(
        "./databases/" + path + "/initial_database.db",
        check_same_thread=False,
    )
    connIni.row_factory = sqlite3.Row
    cursorIni = connIni.cursor()
    connFin = sqlite3.connect(
        "./databases/" + path + "/general_database.db",
        check_same_thread=False,
    )
    connFin.row_factory = sqlite3.Row
    cursorFin = connFin.cursor()
    allChanges = []
    diff1 = setFinal - setInicial
    diff2 = setInicial - setFinal
    listaInicial = []
    listaFinal = []
    dicInicial = {}
    dicFinal = {}

    for k in diff1:
        for index in range(0, len(k)):
            listaInicial.append(k[index])

    for k in diff2:
        for index in range(0, len(k)):
            listaFinal.append(k[index])

    for index in range(0, len(listaInicial) - 1, 2):
        # print("Index: ", index)
        key = listaInicial[index]
        value = listaInicial[index + 1]
        if key in dicFinal:
            dicFinal[key].append(value)
        else:
            dicFinal[key] = [value]
    for index2 in range(0, len(listaFinal) - 1, 2):
        key = listaFinal[index2]
        value = listaFinal[index2 + 1]
        if key in dicInicial:
            dicInicial[key].append(value)
        else:
            dicInicial[key] = [value]

    # CHECK IF THERE ARE TRADES

    for key in dicInicial:
        for i, elem in enumerate(dicInicial[key]):
            elem2 = dicFinal[key][i]
            stmt = """SELECT * FROM aula WHERE id=?"""
            cursorFin.execute(stmt, (key,))
            resultAula = cursorFin.fetchone()
            stmtB = """SELECT * FROM aulaUC WHERE idAula=?"""
            cursorIni.execute(stmtB, (key,))
            resultAulaUC = cursorIni.fetchone()
            stmtDocente = """SELECT * FROM turmas WHERE codigo=?"""
            cursorIni.execute(stmtDocente, (elem,))
            cursorIni.fetchone()
            cursorIni.execute(stmtDocente, (elem2,))
            firstTurma = cursorIni.fetchone()
            change = globalNaturalLanguage(
                "turmasRem",
                resultAulaUC["idUC"],
                resultAula["diaSemana"],
                "",
                converter_horario(resultAula["horaInicial"]),
                "",
                "",
                "",
                firstTurma["codigo"],
                "",
                "",
                "",
                "",
                key,
                "",
                "",
            )
            allChanges.append(change)
    for key in dicFinal:
        for elem in dicFinal[key]:
            stmt = """SELECT * FROM aula WHERE id=?"""
            cursorFin.execute(stmt, (key,))
            resultAula = cursorFin.fetchone()
            stmtB = """SELECT * FROM aulaUC WHERE idAula=?"""
            cursorFin.execute(stmtB, (key,))
            resultAulaUC = cursorFin.fetchone()
            stmtDocente = """SELECT * FROM turmas WHERE codigo=?"""
            cursorFin.execute(stmtDocente, (elem,))
            firstTurma = cursorFin.fetchone()
            change = globalNaturalLanguage(
                "turmasAdd",
                resultAulaUC["idUC"],
                resultAula["diaSemana"],
                "",
                converter_horario(resultAula["horaInicial"]),
                "",
                "",
                "",
                firstTurma["codigo"],
                "",
                "",
                "",
                "",
                key,
                "",
                "",
            )
            allChanges.append(change)
    return allChanges


def handleAulaSala(setFinal, setInicial, ProjectNumber):  # TESTED AND WORKING
    path = "Project" + str(ProjectNumber)
    connIni = sqlite3.connect(
        "./databases/" + path + "/initial_database.db",
        check_same_thread=False,
    )
    connIni.row_factory = sqlite3.Row
    cursorIni = connIni.cursor()
    connFin = sqlite3.connect(
        "./databases/" + path + "/general_database.db",
        check_same_thread=False,
    )
    connFin.row_factory = sqlite3.Row
    cursorFin = connFin.cursor()
    allChanges = []
    diff1 = setFinal - setInicial
    diff2 = setInicial - setFinal
    dicInicial = {}
    dicFinal = {}
    listaInicial = []
    listaFinal = []
    # print("Diff1: ", diff1)
    # print("Diff2: ", diff2)
    # print("Lista Inicial: ", listaInicial)
    # print("Lista Final: ", listaFinal)
    # print("Dic Inicial: ", dicInicial)
    # print("Dic Final: ", dicFinal)
    for k in diff1:
        for index in range(0, len(k)):
            listaInicial.append(k[index])

    for k in diff2:
        for index in range(0, len(k)):
            listaFinal.append(k[index])

    for index in range(0, len(listaInicial) - 1, 2):
        # print("Index: ", index)
        key = listaInicial[index]
        value = listaInicial[index + 1]
        if key in dicFinal:
            dicFinal[key].append(value)
        else:
            dicFinal[key] = [value]
    for index2 in range(0, len(listaFinal) - 1, 2):
        key = listaFinal[index2]
        value = listaFinal[index2 + 1]
        if key in dicInicial:
            dicInicial[key].append(value)
        else:
            dicInicial[key] = [value]
    # CHECK IF THERE ARE TRADES

    for key in dicInicial:
        for elem in dicInicial[key]:
            stmt = """SELECT * FROM aula WHERE id=?"""
            cursorIni.execute(stmt, (key,))
            resultAula = cursorIni.fetchone()
            stmtB = """SELECT * FROM aulaUC WHERE idAula=?"""
            cursorIni.execute(stmtB, (key,))
            resultAulaUC = cursorIni.fetchone()
            stmtTurma = """SELECT * FROM aulaTurmas WHERE idAula=?"""
            cursorIni.execute(stmtTurma, (key,))
            resultTurma = cursorIni.fetchone()
            change = globalNaturalLanguage(
                "salasRem",
                resultAulaUC["idUC"],
                resultAula["diaSemana"],
                "",
                converter_horario(resultAula["horaInicial"]),
                "",
                elem,
                "",
                "",
                "",
                resultTurma["idTurma"],
                "",
                "",
                key,
                "",
                "",
            )
            allChanges.append(change)
    for key in dicFinal:
        for elem in dicFinal[key]:
            stmt = """SELECT * FROM aula WHERE id=?"""
            cursorIni.execute(stmt, (key,))
            resultAula = cursorIni.fetchone()
            stmtB = """SELECT * FROM aulaUC WHERE idAula=?"""
            cursorFin.execute(stmtB, (key,))
            resultAulaUC = cursorFin.fetchone()
            stmtTurma = """SELECT * FROM aulaTurmas WHERE idAula=?"""
            cursorFin.execute(stmtTurma, (key,))
            resultTurma = cursorFin.fetchone()
            # print(f"ResultTurma: {resultTurma}")
            change = globalNaturalLanguage(
                "salasAdd",
                resultAulaUC["idUC"],
                resultAula["diaSemana"],
                "",
                converter_horario(resultAula["horaInicial"]),
                "",
                elem,
                "",
                "",
                "",
                resultTurma["idTurma"],
                "",
                "",
                key,
                "",
                "",
            )
            allChanges.append(change)
    return allChanges


linguagemNatural = {
    "uc": "Aula ({} - {} [Turma: {}]) : UC {} -> UC {}",
    "docentes": "Aula {} ({} - {} [Turma: {}]) : Docente {} -> Docente {}",  # Aula [UC] (DiaSemana - Hora [Turma: 1ªTurma]) : Docente {DocenteRemovido} -> Docente {DocenteAdicionado}
    "docentesAdd": "Aula {} ({} - {} [Turma: {}]) : + Docente {}",  # Aula [UC] (DiaSemana - Hora [Turma: 1ªTurma]) : + Docente {DocenteAdicionado}
    "docentesRem": "Aula {} ({} - {} [Turma: {}]) : - Docente {}",  # Aula [UC] (DiaSemana - Hora [Turma: 1ªTurma]) : - Docente {DocenteRemovido}
    "turmas": "Aula {} ({} - {}) : Turma {} -> Turma {}",  # Aula [UC] (DiaSemana - Hora [Turma: 1ªTurma]) : Docente {DocenteRemovido} -> Docente {DocenteAdicionado}
    "turmasAdd": "Aula {} ({} - {}) : + Turma {}",  # Aula [UC] (DiaSemana - Hora [Turma: 1ªTurma]) : + Docente {DocenteAdicionado}
    "turmasRem": "Aula {} ({} - {}) : - Turma {}",  # Aula [UC] (DiaSemana - Hora [Turma: 1ªTurma]) : - Docente {DocenteRemovido}
    "horario": "Aula {} [Turma: {}] : ({} - [{}-{}]) -> ({} - [{}-{}])",  # Aula [UC] (DiaSemana - Hora [Turma: 1ªTurma]) : (DiaInicial - HoraInicial) -> (DiaFinal - HoraFinal)
    "salasAdd": "Aula {} ({} - {} [Turma : {}]) : + Sala {}",
    "salasRem": "Aula {} ({} - {} [Turma : {}]) : - Sala {}",
    "salas": "Aula {} ({} - {} [Turma : {}]) : Sala {} -> Sala {}",
    "createDocente": "Criar Docente {} - {} - {}",  # Criar Docente (Mecanografico - Nome - Sigla)
    "deleteDocente": "Delete Docente {} - {} - {}",
    ## SORTING:
    # CRIAR DOCENTES
    # MEXER NAS AULAS DOS DOCENTES
    # HORARIOS AULAS
    # SALAS
}


def globalNaturalLanguage(
    tipo,
    uc,
    diaSemanaInicial,
    diaSemanaFinal,
    horaInicialInicial,
    horaInicialFinal,
    salaInicial,
    salaFinal,
    docenteInicial,
    docenteFinal,
    turmaDaAula,
    nomeDocente,
    siglaDocente,
    idAula,
    horaFinalInicial,
    horaFinalFinal,
):

    precedencia = {
        "DOC_CREATE_REMOVE": 1,
        "CLASS_SCHEDULING": 2,
        "UC_CHANGE_CLASS": 3,
        "DOC_CHANGE_CLASS": 4,
        "CLASS_CHANGE_CLASS": 5,
        "CLASSROOM_MANIPULATION": 6,
    }
    if tipo == "uc":
        return (
            precedencia["UC_CHANGE_CLASS"],
            linguagemNatural["uc"].format(
                horaInicialInicial,
                horaFinalInicial,
                turmaDaAula,
                uc,
                docenteFinal,
            ),
            idAula,
        )
    elif tipo == "docentes":
        return (
            precedencia["DOC_CHANGE_CLASS"],
            linguagemNatural["docentes"].format(
                uc,
                diaSemanaInicial,
                horaInicialInicial,
                turmaDaAula,
                docenteInicial,
                docenteFinal,
            ),
            idAula,
        )
    elif tipo == "docentesAdd":
        return (
            precedencia["DOC_CHANGE_CLASS"],
            linguagemNatural["docentesAdd"].format(
                uc,
                diaSemanaInicial,
                horaInicialInicial,
                turmaDaAula,
                docenteInicial,
            ),
            idAula,
        )
    elif tipo == "docentesRem":
        return (
            precedencia["DOC_CHANGE_CLASS"],
            linguagemNatural["docentesRem"].format(
                uc,
                diaSemanaInicial,
                horaInicialInicial,
                turmaDaAula,
                docenteInicial,
            ),
            idAula,
        )
    elif tipo == "turmas":
        return (
            precedencia["CLASS_CHANGE_CLASS"],
            linguagemNatural["turmas"].format(
                uc,
                diaSemanaInicial,
                horaInicialInicial,
                docenteInicial,
                docenteFinal,
            ),
            idAula,
        )
    elif tipo == "turmasAdd":
        return (
            precedencia["CLASS_CHANGE_CLASS"],
            linguagemNatural["turmasAdd"].format(
                uc,
                diaSemanaInicial,
                horaInicialInicial,
                docenteInicial,
            ),
            idAula,
        )
    elif tipo == "turmasRem":
        return (
            precedencia["CLASS_CHANGE_CLASS"],
            linguagemNatural["turmasRem"].format(
                uc,
                diaSemanaInicial,
                horaInicialInicial,
                docenteInicial,
            ),
            idAula,
        )
    elif tipo == "horario":
        return (
            precedencia["CLASS_SCHEDULING"],
            linguagemNatural["horario"].format(
                uc,
                turmaDaAula,
                diaSemanaInicial,
                horaInicialInicial,
                horaFinalInicial,
                diaSemanaFinal,
                horaInicialFinal,
                horaFinalFinal,
            ),
            idAula,
        )  # change
    elif tipo == "salasAdd":
        return (
            precedencia["CLASSROOM_MANIPULATION"],
            linguagemNatural["salasAdd"].format(
                uc,
                diaSemanaInicial,
                horaInicialInicial,
                turmaDaAula,
                salaInicial,
            ),
            idAula,
        )
    elif tipo == "salasRem":
        return (
            precedencia["CLASSROOM_MANIPULATION"],
            linguagemNatural["salasRem"].format(
                uc,
                diaSemanaInicial,
                horaInicialInicial,
                turmaDaAula,
                salaInicial,
            ),
            idAula,
        )
    elif tipo == "salas":
        return (
            precedencia["CLASSROOM_MANIPULATION"],
            linguagemNatural["salas"].format(
                uc,
                diaSemanaInicial,
                horaInicialInicial,
                turmaDaAula,
                salaInicial,
                salaFinal,
            ),
            idAula,
        )
    elif tipo == "createDocente":
        return (
            precedencia["DOC_CREATE_REMOVE"],
            linguagemNatural["createDocente"].format(
                docenteInicial,
                nomeDocente,
                siglaDocente,
            ),
            0,
        )
    elif tipo == "removeDocente":
        return (
            precedencia["DOC_CREATE_REMOVE"],
            linguagemNatural["removeDocente"].format(
                docenteInicial,
                nomeDocente,
                siglaDocente,
            ),
            0,
        )


def append_aula_data(row_dict):
    hora_inicio = row_dict.get("horaInicial")
    duracao = row_dict.get("duracao")

    # Check if hora_inicio is valid (not None or 0)
    if hora_inicio is None or hora_inicio == 0:
        hora_inicio = "0"
    else:
        hora_inicio = str(hora_inicio)  # Ensure it's a string

    # Convert hora_inicio to the proper HH:MM format
    hora_inicio = converter_horario(int(hora_inicio)) if hora_inicio != "0" else "00:00"

    # Calculate hora_fim based on the duration
    if duracao is None or duracao == 0:
        hora_fim = "0"
    else:
        hora_fim = calculate_hora_final(
            hora_inicio,
            duracao,
        )  # Use calculate_hora_final for hora_fim
        hora_fim = converter_horario(hora_fim)  # Convert hora_fim to HH:MM format

    # Prepare the data dictionary for AulaInfo
    data = {
        "aulaId": row_dict.get("id"),
        "cadeiraId": row_dict.get("idUc"),
        "horaInicio": hora_inicio,
        "horaFim": hora_fim,
        "dia": row_dict.get("diaSemana"),
        "turmasIds": [row_dict.get("idTurma")] if "idTurma" in row_dict else [],
        "docentesIds": [row_dict.get("idDocente")] if "idDocente" in row_dict else [],
        "salasIds": [row_dict.get("idSala")] if "idSala" in row_dict else [],
    }

    # Return the processed data which can be used to create an AulaInfo instance
    return data


def fetch_list(cursor, query):
    cursor.execute(query)
    return {row[0] for row in cursor.fetchall()}


def diff_checker(aula_id, cursorDB, cursorIni):
    queries = {
        "turmas": f"SELECT idTurma FROM aulaTurmas WHERE idAula = {aula_id};",
        "docentes": f"SELECT idDocente FROM aulaDocente WHERE idAula = {aula_id};",
        "salas": f"SELECT idSala FROM aulaSala WHERE idAula = {aula_id};",
        "ucs": f"SELECT idUC FROM aulaUC WHERE idAula = {aula_id};",
    }

    old_data = {}
    for key, query in queries.items():
        old_data[key] = fetch_list(cursorIni, query)

    new_data = {}
    for key, query in queries.items():
        new_data[key] = fetch_list(cursorDB, query)

    return old_data != new_data


def getDifferencesFromDatabases(ProjectNumber):
    # there may be new docentes in the general database associated to existing ids but have no code
    changesList = []  # Stores all changes in AulaInfo format

    path = f"Project{ProjectNumber}"
    db_path = f"./databases/{path}/general_database.db"
    print(f"Trying to connect to: {db_path}")
    connDB = sqlite3.connect(db_path, check_same_thread=False)
    connDB.row_factory = sqlite3.Row
    cursorDB = connDB.cursor()

    connIni = sqlite3.connect(
        f"./databases/{path}/initial_database.db",
        check_same_thread=False,
    )
    connIni.row_factory = sqlite3.Row
    cursorIni = connIni.cursor()

    cursorDB.execute("SELECT * FROM aula;")
    data2 = cursorDB.fetchall()

    cursorIni.execute("SELECT * FROM aula;")
    data1 = cursorIni.fetchall()

    # Create dictionaries to map aulaId to row data for quick lookups
    db1_aulas = {row["id"]: row for row in data1}
    db2_aulas = {row["id"]: row for row in data2}

    # Compare rows from both databases
    for aula_id, row1 in db1_aulas.items():
        row2 = db2_aulas.get(aula_id)  # Get corresponding row from the second database

        if row2 is None:
            # If row2 is None, the aula was removed (it exists in the initial database but not the new one)
            row_dict = dict(row1)
            print("Starting data (removed):", row_dict)

            # Process associated data for the removed aula
            old_aula = get_aula_info(aula_id, cursorIni, row_dict)
            change = AulaChange(old_aula, None)
            if change.has_changes():
                changesList.append(change)  # Store added aula  # Store removed aula

        else:
            # If row2 exists, compare the two rows for differences
            if row1 != row2 or diff_checker(aula_id, cursorDB, cursorIni):
                row_dict1 = dict(row1)
                row_dict2 = dict(row2)

                print("Starting data (old):", row_dict1)
                print("Starting data (new):", row_dict2)
                # Get associated data for both rows
                old_aula = get_aula_info(aula_id, cursorIni, row_dict1)
                new_aula = get_aula_info(aula_id, cursorDB, row_dict2)

                # Append the change
                change = AulaChange(old_aula, new_aula)
                if change.has_changes():
                    changesList.append(change)

    # Check for aulas that exist only in the second database (added rows)
    for aula_id, row2 in db2_aulas.items():
        if aula_id not in db1_aulas:
            row_dict = dict(row2)
            print("Starting data (new):", row_dict)

            # Process associated data for the added aula
            new_aula = get_aula_info(aula_id, cursorDB, row_dict)
            change = AulaChange(None, new_aula)
            if change.has_changes():
                changesList.append(change)  # Store added aula

    # Print changes
    print("\nDetected Changes:")
    for aula_change in changesList:
        print(f"Previous: {aula_change.previous}")
        print(f"New: {aula_change.new}")

    serialized_changes = []
    for change in changesList:
        serialized_change = {
            "previous": change.previous.to_dict() if change.previous else None,
            "new": change.new.to_dict() if change.new else None,
        }
        serialized_changes.append(serialized_change)

    # Ensure output directory exists
    output_dir = f"./databases/Project{ProjectNumber}/"
    os.makedirs(output_dir, exist_ok=True)

    # Write to JSON file
    output_file = os.path.join(output_dir, "changes.json")

    if os.path.exists(output_file):
        os.remove(output_file)
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(serialized_changes, f, ensure_ascii=False, indent=4)

    print(f"\nChanges saved to {output_file}")
    return changesList


def get_aula_info(aula_id, cursorDB, row_dict):
    """Helper function to retrieve and process associated data for a given aula record"""

    # Get associated 'turmas' (class groups) for the aula
    cursorDB.execute(
        f"""
        SELECT t.codigo
        FROM aulaTurmas at
        JOIN turmas t ON at.idTurma = t.codigo
        WHERE at.idAula = {aula_id};
    """,
    )
    turmas = [row[0] for row in cursorDB.fetchall()]

    # Get associated 'docentes' (teachers) for the aula
    cursorDB.execute(
        f"""
        SELECT d.numeroMecanografico, d.nome
        FROM aulaDocente ad
        JOIN docentes d ON ad.idDocente = d.numeroMecanografico
        WHERE ad.idAula = {aula_id};
    """,
    )
    docentes = [row[0] for row in cursorDB.fetchall()]
    docentes_names = [row[1] for row in cursorDB.fetchall()]

    # Get associated 'salas' (rooms) for the aula
    cursorDB.execute(
        f"""
        SELECT s.numero
        FROM aulaSala as aula_sala
        JOIN salas s ON aula_sala.idSala = s.numero
        WHERE aula_sala.idAula = {aula_id};
    """,
    )
    salas = [row[0] for row in cursorDB.fetchall()]

    # Get associated 'UC' (unit courses) for the aula
    cursorDB.execute(
        """
    SELECT uc.codigo
    FROM aulaUC auc
    JOIN uc ON auc.idUC = uc.codigo
    WHERE auc.idAula = ?;
    """,
        (aula_id,),
    )  # Using placeholder for aula_id
    uc = [row[0] for row in cursorDB.fetchall()]

    if uc:
        uc_codigo = uc[0]
        cursorDB.execute(
            """
            SELECT uc.nome
            FROM uc
            WHERE uc.codigo = ?;
        """,
            (uc_codigo,),
        )  # Using placeholder for uc_codigo
        uc_name = [row[0] for row in cursorDB.fetchall()]

    # Create AulaInfo from row_dict and the associated data
    data = append_aula_data(row_dict)
    data["turmasIds"] = turmas
    data["docentesIds"] = docentes
    data["salasIds"] = salas
    data["cadeiraId"] = uc[0]
    aula = AulaInfo.from_data(data)
    aula.set_docentes_names(docentes_names)
    aula.uc_name = uc_name[0]
    return aula


def debug_log_existing_aulas(project_number, dia_semana):
    """Logs the existing aulas from the database for the given project number and day"""

    # Construct the database path
    db_path = Path(f"./databases/Project{project_number}/general_database.db")
    try:
        # Connect to the database
        connection = sqlite3.connect(str(db_path))
        cursor = connection.cursor()

        # Log existing aula data for the specified day
        print(
            f"\n[DEBUG] Existing aulas on dia_semana={dia_semana} for Project {project_number}",
        )
        cursor.execute(
            """
            SELECT a.id, a.horaInicial, a.duracao, a.diaSemana,
                   GROUP_CONCAT(DISTINCT asl.idSala),
                   GROUP_CONCAT(DISTINCT ad.idDocente),
                   GROUP_CONCAT(DISTINCT at.idTurma),
                   uc.nome
            FROM aula a
            LEFT JOIN aulaSala asl ON a.id = asl.idAula
            LEFT JOIN aulaDocente ad ON a.id = ad.idAula
            LEFT JOIN aulaTurmas at ON a.id = at.idAula
            JOIN aulaUC auc ON a.id = auc.idAula
            JOIN uc ON auc.idUC = uc.codigo
            WHERE a.diaSemana = ?
            GROUP BY a.id
        """,
            (dia_semana,),
        )

        rows = cursor.fetchall()
        for row in rows:
            print(
                f"[AULA] ID: {row[0]} | START: {row[1]} | DURACAO: {row[2]} | DIA: {row[3]} | "
                f"SALAS: {row[4]} | DOCENTES: {row[5]} | TURMAS: {row[6]} | UC: {row[7]}",
            )
    except sqlite3.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")
    finally:
        if "cursor" in locals():
            cursor.close()
        if "connection" in locals():
            connection.close()


def organize_changes(ProjectId, mode, validator):
    # TODO organize
    json_path = f"./databases/Project{ProjectId}/changes.json"

    if os.path.exists(json_path) and validator:
        with open(json_path, encoding="utf-8") as f:
            raw_changes = json.load(f)

        changes = []
        for change in raw_changes:
            prev = models.AulaInfo.from_data(change["previous"]) if change["previous"] else None
            new = models.AulaInfo.from_data(change["new"]) if change["new"] else None
            if prev:
                prev.uc_name = change["previous"].get("uc_name", "")
                prev.do = change["previous"].get("uc_name", "")
            if new:
                new.uc_name = change["new"].get("uc_name", "")
            changes.append(models.AulaChange(prev, new))
    else:
        changes = getDifferencesFromDatabases(ProjectId)

    manager = models.GraphManager(ProjectId, mode)
    path = f"Project{ProjectId}"
    db_path = f"./databases/{path}/general_database.db"
    connDB = sqlite3.connect(db_path, check_same_thread=False)
    connDB.row_factory = sqlite3.Row
    cursorDB = connDB.cursor()

    db_path = f"./databases/{path}/initial_database.db"
    connIni = sqlite3.connect(db_path, check_same_thread=False)
    connIni.row_factory = sqlite3.Row
    cursorIni = connIni.cursor()

    for change in changes:
        cursorIni.execute(
            f"""
        SELECT d.numeroMecanografico, d.nome
        FROM aulaDocente ad
        JOIN docentes d ON ad.idDocente = d.numeroMecanografico
        WHERE ad.idAula = {change.previous.id};
        """,
        )
        names_ini = [row[1] for row in cursorIni.fetchall()]
        change.previous.set_docentes_names(names_ini)

        cursorDB.execute(
            f"""
        SELECT d.numeroMecanografico, d.nome
        FROM aulaDocente ad
        JOIN docentes d ON ad.idDocente = d.numeroMecanografico
        WHERE ad.idAula = {change.new.id};
        """,
        )
        names_new = [row[1] for row in cursorDB.fetchall()]

        change.new.set_docentes_names(names_new)
        node = models.Node(change)
        manager.add_node(node)
    print("====Finished operations====")
    manager.create_local_edges()
    manager.update_local_edges()
    manager.default_order()

    return manager
    # it should return a datastructure in the format of a list of tuples. Here's the format of the tuples expected
    # (Node, string tipodetroca, [int, int, int, ...])
    # tipodetroca can be ok, conflict, circular_dependency, upcoming_changes
    # the list should be ordered, by the order to export (root nodes are the first for each group of turma or UC)
    # the list of ints is a list of node IDs. it will depending on tipodetroca, they can represent a list of
    #   node IDs that cause conflict with - tipodetroca "conflict"
    #   node IDs from changes that solve "fake" conflicts, but will only appear later in the list - tipodetroca "upcoming_changes"
    #   node IDs that form a circular dependency with - tipodetroca "circular_dependency"
    #   empty list if tipodetroca is "ok"
