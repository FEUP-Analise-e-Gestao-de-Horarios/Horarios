from getHorariosFromDB.conflictFunctionsDup import findAnyConflicts
from getHorariosFromDB.auxiliaryScheduleFunctions import getInformationFromAula
from getHorariosFromDB.auxiliaryScheduleFunctions import getAbreviacaoFromMecanografico
import sqlite3
import shutil
import networkx as nx
from networkx import dfs_tree

changeOrder = 1

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

def diferenca_horas(hora1, hora2):
    # Extrair horas e minutos das horas em formato inteiro
    hora1_h, hora1_m = divmod(hora1, 100)
    hora2_h, hora2_m = divmod(hora2, 100)

    # Calcular diferença em minutos
    diff_minutes = (hora2_h * 60 + hora2_m) - (hora1_h * 60 + hora1_m)

    # Calcular diferença em horas, incluindo meias horas
    diff_hours = diff_minutes / 60.0
    diff_hours = round(diff_hours, 1) # arredondar para uma casa decimal

    return diff_hours


     

linguagemNatural = {
    "uc" : "Aula ({} - {} [Turma: {}]) : UC {} -> UC {}",
    "docentes" : "Aula {} ({} - {} [Turma: {}]) : Docente {} -> Docente {}", # Aula [UC] (DiaSemana - Hora [Turma: 1ªTurma]) : Docente {DocenteRemovido} -> Docente {DocenteAdicionado}
    "docentesAdd" : "Aula {} ({} - {} [Turma: {}]) : + Docente {}", # Aula [UC] (DiaSemana - Hora [Turma: 1ªTurma]) : + Docente {DocenteAdicionado}
    "docentesRem" : "Aula {} ({} - {} [Turma: {}]) : - Docente {}", # Aula [UC] (DiaSemana - Hora [Turma: 1ªTurma]) : - Docente {DocenteRemovido}
    "turmas" : "Aula {} ({} - {}) : Turma {} -> Turma {}", # Aula [UC] (DiaSemana - Hora [Turma: 1ªTurma]) : Docente {DocenteRemovido} -> Docente {DocenteAdicionado}
    "turmasAdd" : "Aula {} ({} - {}) : + Turma {}", # Aula [UC] (DiaSemana - Hora [Turma: 1ªTurma]) : + Docente {DocenteAdicionado}
    "turmasRem" : "Aula {} ({} - {}) : - Turma {}", # Aula [UC] (DiaSemana - Hora [Turma: 1ªTurma]) : - Docente {DocenteRemovido}
    "horario" : "Aula {} [Turma: {}] : ({} - [{}-{}]) -> ({} - [{}-{}])", # Aula [UC] (DiaSemana - Hora [Turma: 1ªTurma]) : (DiaInicial - HoraInicial) -> (DiaFinal - HoraFinal)
    "salasAdd" : "Aula {} ({} - {} [Turma : {}]) : + Sala {}",
    "salasRem" : "Aula {} ({} - {} [Turma : {}]) : - Sala {}",
    "salas" : "Aula {} ({} - {} [Turma : {}]) : Sala {} -> Sala {}",
    "createDocente" : "Criar Docente {} - {} - {}", # Criar Docente (Mecanografico - Nome - Sigla)
    "deleteDocente" : "Delete Docente {} - {} - {}"

    ## SORTING:

    # CRIAR DOCENTES
    # MEXER NAS AULAS DOS DOCENTES
    # HORARIOS AULAS
    # SALAS
}

#ACRESCENTAR SIGLA UC

def globalNaturalLanguage(tipo, uc, diaSemanaInicial, diaSemanaFinal, horaInicialInicial, horaInicialFinal, salaInicial, salaFinal, docenteInicial, docenteFinal, turmaDaAula, nomeDocente, siglaDocente, idAula, horaFinalInicial, horaFinalFinal):

    precedencia = {"DOC_CREATE_REMOVE" : 1, "CLASS_SCHEDULING" : 2, "UC_CHANGE_CLASS" : 3, "DOC_CHANGE_CLASS" : 4, "CLASS_CHANGE_CLASS" : 5, "CLASSROOM_MANIPULATION" : 6}
    if tipo=="uc":
        return (precedencia["UC_CHANGE_CLASS"], linguagemNatural["uc"].format(horaInicialInicial, horaFinalInicial, turmaDaAula, uc, docenteFinal), idAula)
    elif tipo=="docentes":
        return (precedencia["DOC_CHANGE_CLASS"] , linguagemNatural["docentes"].format(uc, diaSemanaInicial, horaInicialInicial, turmaDaAula, docenteInicial, docenteFinal), idAula)
    elif tipo=="docentesAdd":
        return (precedencia["DOC_CHANGE_CLASS"] , linguagemNatural["docentesAdd"].format(uc, diaSemanaInicial, horaInicialInicial, turmaDaAula, docenteInicial), idAula)
    elif tipo=="docentesRem":
        return (precedencia["DOC_CHANGE_CLASS"] , linguagemNatural["docentesRem"].format(uc, diaSemanaInicial, horaInicialInicial, turmaDaAula, docenteInicial), idAula)
    elif tipo=="turmas":
        return (precedencia["CLASS_CHANGE_CLASS"] , linguagemNatural["turmas"].format(uc, diaSemanaInicial, horaInicialInicial, docenteInicial, docenteFinal), idAula)
    elif tipo=="turmasAdd":
        return (precedencia["CLASS_CHANGE_CLASS"] , linguagemNatural["turmasAdd"].format(uc, diaSemanaInicial, horaInicialInicial, docenteInicial), idAula)
    elif tipo=="turmasRem":
        return (precedencia["CLASS_CHANGE_CLASS"] , linguagemNatural["turmasRem"].format(uc, diaSemanaInicial, horaInicialInicial, docenteInicial), idAula)
    elif tipo == "horario":
        return (precedencia["CLASS_SCHEDULING"] , linguagemNatural["horario"].format(uc, turmaDaAula, diaSemanaInicial, horaInicialInicial, horaFinalInicial ,diaSemanaFinal, horaInicialFinal, horaFinalFinal), idAula) #change
    elif tipo == "salasAdd":
        return (precedencia["CLASSROOM_MANIPULATION"] , linguagemNatural["salasAdd"].format(uc, diaSemanaInicial, horaInicialInicial, turmaDaAula, salaInicial), idAula)
    elif tipo == "salasRem":
        return (precedencia["CLASSROOM_MANIPULATION"] , linguagemNatural["salasRem"].format(uc, diaSemanaInicial, horaInicialInicial, turmaDaAula, salaInicial), idAula)
    elif tipo == "salas":
        return (precedencia["CLASSROOM_MANIPULATION"] , linguagemNatural["salas"].format(uc, diaSemanaInicial, horaInicialInicial, turmaDaAula, salaInicial, salaFinal), idAula)
    elif tipo == "createDocente":
        return (precedencia["DOC_CREATE_REMOVE"] , linguagemNatural["createDocente"].format(docenteInicial, nomeDocente, siglaDocente), 0)
    elif tipo == "removeDocente":
        return (precedencia["DOC_CREATE_REMOVE"] , linguagemNatural["removeDocente"].format(docenteInicial, nomeDocente, siglaDocente), 0)


def handleAulas(setFinal, setInicial, ProjectNumber):
    path = "Project" + str(ProjectNumber)
    connIni = sqlite3.connect('./database/' + path + '/initial_database.db', check_same_thread=False)
    connIni.row_factory = sqlite3.Row
    cursorIni = connIni.cursor()
    allChanges = []
    diff1 = setFinal-setInicial
    diff2 = setInicial-setFinal
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
        for l in range(0, 4):
            listaInicial.append(k[l])    
    for k in diff2:
        for l in range(0, 4):
            listaFinal.append(k[l])

    for i, item in enumerate(listaInicial):
        if i % 4 == 0:
            key = item
            values = tuple(listaInicial[i+1:i+4])
            dicFinal[key] = values
    for i, item in enumerate(listaFinal):
        if i % 4 == 0:
            key = item
            values = tuple(listaFinal[i+1:i+4])
            dicInicial[key] = values

    # CHECK IF THERE ARE TRADES
    
    for key in dicInicial:
        if key in dicFinal:
            stmtB = '''SELECT * FROM aulaUC WHERE idAula=?'''
            cursorIni.execute(stmtB, (key,))
            resultAulaUC = cursorIni.fetchone()
            stmtTurma = '''SELECT * FROM aulaTurmas WHERE idAula=?'''
            cursorIni.execute(stmtTurma, (key,))
            resultTurma = cursorIni.fetchone()
            horaFinalInicial =  converter_horario(calculate_hora_final(converter_horario(dicInicial[key][0]),dicInicial[key][1]))
            horaFinalFinal = converter_horario(calculate_hora_final(converter_horario(dicFinal[key][0]),dicFinal[key][1]))
            change = globalNaturalLanguage("horario", resultAulaUC["idUc"], dicInicial[key][2], dicFinal[key][2], converter_horario(dicInicial[key][0]), converter_horario(dicFinal[key][0]), "", "", "", "", resultTurma["idTurma"], "", "", key, horaFinalInicial, horaFinalFinal)
            allChanges.append(change)
    return allChanges

def handleSalas(setFinal, setInicial, ProjectNumber): # TESTED AND WORKING
    allChanges = []
    diff1 = setFinal-setInicial
    lista1 = []
    diff2 = setInicial-setFinal
    lista2 = []
    for elem in diff1:
        lista1.append(elem)
    for elem2 in diff2:
        lista2.append(elem2)
    for newSala in lista1:
        change = globalNaturalLanguage("salasAdd", "", "", "", "", "", newSala["numero"], "", "", "" , "", "", "", "", "", "")
        allChanges.append(change)
    for delSala in lista2:
        change = globalNaturalLanguage("salasRem", "", "", "", "", "", delSala["numero"], "", "", "" , "", "", "", "", "", "")
        allChanges.append(change)
    return allChanges    
        
def handleDocentes(setFinal, setInicial, ProjectNumber): # TESTED AND WORKING
    allChanges = []
    diff1 = setFinal-setInicial
    lista1 = []
    diff2 = setInicial-setFinal
    lista2 = []
    for elem in diff1:
        lista1.append(elem)
    for elem2 in diff2:
        lista2.append(elem2)
    for newDocente in lista1:
        change = globalNaturalLanguage("createDocente", "", "", "", "", "", "", "", newDocente["numeroMecanografico"], "", "", newDocente["nome"], newDocente["abreviacao"], "", "", "")
        allChanges.append(change)
    for delDocente in lista2:
        change = globalNaturalLanguage("removeDocente", "", "", "", "", "", "", "", delDocente["numeroMecanografico"], "", "", delDocente["nome"], delDocente["abreviacao"], "", "", "")
        allChanges.append(change)
    return allChanges

def handleAulaDocente(setFinal, setInicial, ProjectNumber): # TESTED AND WORKING
    path = "Project" + str(ProjectNumber)
    connIni = sqlite3.connect('./database/' + path + '/initial_database.db', check_same_thread=False)
    connIni.row_factory = sqlite3.Row
    cursorIni = connIni.cursor()
    connFin = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    connFin.row_factory = sqlite3.Row
    cursorFin = connFin.cursor()
    allChanges = []
    diff1 = setFinal-setInicial
    diff2 = setInicial-setFinal
   
    listaInicial = []
    listaFinal = []
    dicInicial = {}
    dicFinal = {}

    for k in diff1:
        for l in range(0, len(k)):
            listaInicial.append(k[l])
    
    for k in diff2:
        for l in range(0, len(k)):
            listaFinal.append(k[l])


    for index in range(0, len(listaInicial)-1, 2):
        # print("Index: ", index)
        key = listaInicial[index]
        value = listaInicial[index+1]
        if key in dicFinal:
            dicFinal[key].append(value)
        else:    
            dicFinal[key] = [value]
    for index2 in range(0, len(listaFinal)-1, 2):
        key = listaFinal[index2]
        value = listaFinal[index2+1]
        if key in dicInicial:
            dicInicial[key].append(value)
        else:    
            dicInicial[key] = [value]

    # CHECK IF THERE ARE TRADES
    

    for key in dicInicial:
        for i, elem in enumerate(dicInicial[key]):
            stmt = '''SELECT * FROM aula WHERE id=?'''
            cursorFin.execute(stmt, (key,))
            resultAula = cursorFin.fetchone()
            stmtB = '''SELECT * FROM aulaUC WHERE idAula=?'''
            cursorIni.execute(stmtB, (key,))
            resultAulaUC = cursorIni.fetchone()
            stmtTurma = '''SELECT * FROM aulaTurmas WHERE idAula=?'''
            cursorIni.execute(stmtTurma, (key,))
            resultTurma = cursorIni.fetchone()
            stmtDocente = '''SELECT * FROM docentes WHERE numeroMecanografico=?'''
            cursorIni.execute(stmtDocente, (elem,))
            lastDocente = cursorIni.fetchone()
            change = globalNaturalLanguage("docentesRem", resultAulaUC["idUC"], resultAula["diaSemana"], "", converter_horario(resultAula["horaInicial"]), "", "", "", lastDocente["abreviacao"], "", resultTurma["idTurma"], "", "", key, "", "")
            allChanges.append(change)
    for key in dicFinal:
        for i, elem in enumerate(dicFinal[key]): 
            stmt = '''SELECT * FROM aula WHERE id=?'''
            cursorFin.execute(stmt, (key,))
            resultAula = cursorFin.fetchone()
            stmtB = '''SELECT * FROM aulaUC WHERE idAula=?'''
            cursorFin.execute(stmtB, (key,))
            resultAulaUC = cursorFin.fetchone()
            stmtTurma = '''SELECT * FROM aulaTurmas WHERE idAula=?'''
            cursorFin.execute(stmtTurma, (key,))
            resultTurma = cursorFin.fetchone()
            stmtDocente = '''SELECT * FROM docentes WHERE numeroMecanografico=?'''
            cursorFin.execute(stmtDocente, (elem,))
            firstDocente = cursorFin.fetchone()
            change = globalNaturalLanguage("docentesAdd", resultAulaUC["idUC"], resultAula["diaSemana"], "", converter_horario(resultAula["horaInicial"]), "", "", "", firstDocente["abreviacao"], "", resultTurma["idTurma"], "", "", key, "", "")
            allChanges.append(change)
    return allChanges

def handleAulaUC(setFinal, setInicial, ProjectNumber): # TESTED AND WORKING
    path = "Project" + str(ProjectNumber)
    connIni = sqlite3.connect('./database/' + path + '/initial_database.db', check_same_thread=False)
    connIni.row_factory = sqlite3.Row
    cursorIni = connIni.cursor()
    connFin = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    connFin.row_factory = sqlite3.Row
    cursorFin = connFin.cursor()
    allChanges = []
    diff1 = setFinal-setInicial
    diff2 = setInicial-setFinal
   
    listaInicial = []
    listaFinal = []
    dicInicial = {}
    dicFinal = {}

    for k in diff1:
        for l in range(0, len(k)):
            listaInicial.append(k[l])
    
    for k in diff2:
        for l in range(0, len(k)):
            listaFinal.append(k[l])


    for index in range(0, len(listaInicial)-1, 2):
        # print("Index: ", index)
        key = listaInicial[index]
        value = listaInicial[index+1]
        if key in dicFinal:
            dicFinal[key].append(value)
        else:    
            dicFinal[key] = [value]
    for index2 in range(0, len(listaFinal)-1, 2):
        key = listaFinal[index2]
        value = listaFinal[index2+1]
        if key in dicInicial:
            dicInicial[key].append(value)
        else:    
            dicInicial[key] = [value]

    # CHECK IF THERE ARE TRADES
    print(f"ALL CHANGES GOING INTO UC: DicFinal: {dicFinal}, DicInicial: {dicInicial}")


    for key in dicInicial:
        for i, elem in enumerate(dicInicial[key]):
            stmt = '''SELECT * FROM aula WHERE id=?'''
            cursorFin.execute(stmt, (key,))
            resultAula = cursorFin.fetchone()
            stmtTurma = '''SELECT * FROM aulaTurmas WHERE idAula=?'''
            cursorIni.execute(stmtTurma, (key,))
            resultTurma = cursorIni.fetchone()
            elem2 = dicFinal[key][i]
            change = globalNaturalLanguage("uc", elem, resultAula["diaSemana"], "", converter_horario(resultAula["horaInicial"]), "", "" ,"", "", elem2, resultTurma["idTurma"], "", "", key, "", "")
            allChanges.append(change)
    return allChanges


def handleAulaTurmas(setFinal, setInicial, ProjectNumber): # TESTED AND WORKING
    path = "Project" + str(ProjectNumber)
    connIni = sqlite3.connect('./database/' + path + '/initial_database.db', check_same_thread=False)
    connIni.row_factory = sqlite3.Row
    cursorIni = connIni.cursor()
    connFin = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    connFin.row_factory = sqlite3.Row
    cursorFin = connFin.cursor()
    allChanges = []
    diff1 = setFinal-setInicial
    diff2 = setInicial-setFinal
    listaInicial = []
    listaFinal = []
    dicInicial = {}
    dicFinal = {}

    for k in diff1:
        for l in range(0, len(k)):
            listaInicial.append(k[l])
    
    for k in diff2:
        for l in range(0, len(k)):
            listaFinal.append(k[l])

    for index in range(0, len(listaInicial)-1, 2):
        # print("Index: ", index)
        key = listaInicial[index]
        value = listaInicial[index+1]
        if key in dicFinal:
            dicFinal[key].append(value)
        else:    
            dicFinal[key] = [value]
    for index2 in range(0, len(listaFinal)-1, 2):
        key = listaFinal[index2]
        value = listaFinal[index2+1]
        if key in dicInicial:
            dicInicial[key].append(value)
        else:    
            dicInicial[key] = [value]

    # CHECK IF THERE ARE TRADES

    for key in dicInicial:
        for i, elem in enumerate(dicInicial[key]):
            elem2 = dicFinal[key][i]
            stmt = '''SELECT * FROM aula WHERE id=?'''
            cursorFin.execute(stmt, (key,))
            resultAula = cursorFin.fetchone()
            stmtB = '''SELECT * FROM aulaUC WHERE idAula=?'''
            cursorIni.execute(stmtB, (key,))
            resultAulaUC = cursorIni.fetchone()
            stmtDocente = '''SELECT * FROM turmas WHERE codigo=?'''
            cursorIni.execute(stmtDocente, (elem,))
            lastTurma = cursorIni.fetchone()
            cursorIni.execute(stmtDocente, (elem2,))
            firstTurma = cursorIni.fetchone()
            change = globalNaturalLanguage("turmasRem", resultAulaUC["idUC"], resultAula["diaSemana"], "", converter_horario(resultAula["horaInicial"]), "", "", "", firstTurma["codigo"], "", "", "", "", key, "", "")
            allChanges.append(change)
    for key in dicFinal:
        for i, elem in enumerate(dicFinal[key]):  
            stmt = '''SELECT * FROM aula WHERE id=?'''
            cursorFin.execute(stmt, (key,))
            resultAula = cursorFin.fetchone()
            stmtB = '''SELECT * FROM aulaUC WHERE idAula=?'''
            cursorFin.execute(stmtB, (key,))
            resultAulaUC = cursorFin.fetchone()
            stmtDocente = '''SELECT * FROM turmas WHERE codigo=?'''
            cursorFin.execute(stmtDocente, (elem,))
            firstTurma = cursorFin.fetchone()
            change = globalNaturalLanguage("turmasAdd", resultAulaUC["idUC"], resultAula["diaSemana"], "", converter_horario(resultAula["horaInicial"]), "", "", "", firstTurma["codigo"], "", "", "", "", key, "", "")
            allChanges.append(change)
    return allChanges


def handleAulaSala(setFinal, setInicial, ProjectNumber): # TESTED AND WORKING
    path = "Project" + str(ProjectNumber)
    connIni = sqlite3.connect('./database/' + path + '/initial_database.db', check_same_thread=False)
    connIni.row_factory = sqlite3.Row
    cursorIni = connIni.cursor()
    connFin = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    connFin.row_factory = sqlite3.Row
    cursorFin = connFin.cursor()
    allChanges = []
    diff1 = setFinal-setInicial
    diff2 = setInicial-setFinal
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
        for l in range(0, len(k)):
            listaInicial.append(k[l])
    
    for k in diff2:
        for l in range(0, len(k)):
            listaFinal.append(k[l])
    
    for index in range(0, len(listaInicial)-1, 2):
        # print("Index: ", index)
        key = listaInicial[index]
        value = listaInicial[index+1]
        if key in dicFinal:
            dicFinal[key].append(value)
        else:    
            dicFinal[key] = [value]
    for index2 in range(0, len(listaFinal)-1, 2):
        key = listaFinal[index2]
        value = listaFinal[index2+1]
        if key in dicInicial:
            dicInicial[key].append(value)
        else:    
            dicInicial[key] = [value]
    # CHECK IF THERE ARE TRADES


    for key in dicInicial:
        for i, elem in enumerate(dicInicial[key]):
            elem2 = dicFinal[key][i]
            stmt = '''SELECT * FROM aula WHERE id=?'''
            cursorIni.execute(stmt, (key,))
            resultAula = cursorIni.fetchone()
            stmtB = '''SELECT * FROM aulaUC WHERE idAula=?'''
            cursorIni.execute(stmtB, (key,))
            resultAulaUC = cursorIni.fetchone()
            stmtTurma = '''SELECT * FROM aulaTurmas WHERE idAula=?'''
            cursorIni.execute(stmtTurma, (key,))
            resultTurma = cursorIni.fetchone()
            change = globalNaturalLanguage("salasRem", resultAulaUC["idUC"], resultAula["diaSemana"], "", converter_horario(resultAula["horaInicial"]), "", elem, "", "", "", resultTurma["idTurma"], "", "", key, "", "")
            allChanges.append(change)
    for key in dicFinal:
        for i, elem in enumerate(dicFinal[key]):
            stmt = '''SELECT * FROM aula WHERE id=?'''
            cursorIni.execute(stmt, (key,))
            resultAula = cursorIni.fetchone()
            stmtB = '''SELECT * FROM aulaUC WHERE idAula=?'''
            cursorFin.execute(stmtB, (key,))
            resultAulaUC = cursorFin.fetchone()
            stmtTurma = '''SELECT * FROM aulaTurmas WHERE idAula=?'''
            cursorFin.execute(stmtTurma, (key,))
            resultTurma = cursorFin.fetchone()
            # print(f"ResultTurma: {resultTurma}")
            change = globalNaturalLanguage("salasAdd", resultAulaUC["idUC"], resultAula["diaSemana"], "", converter_horario(resultAula["horaInicial"]), "", elem, "", "", "", resultTurma["idTurma"], "", "", key, "", "")
            allChanges.append(change)
    return allChanges
            

def sortChanges(item):
    # print(f"Item: {item}")
    (precedence, string, id) = item
    return (id, precedence)

def addChangeToDict(changesDict, table_name, primaryKey, diff_data1, diff_data2):
    # print("Table: ", table_name)
    # print("Primary Key: ", primaryKey)

    new_changes = [dict(row) for row in diff_data1]
    prev_changes = [dict(row) for row in diff_data2]

    for prev in prev_changes:
        for new in new_changes:
            if prev[primaryKey] == new[primaryKey]:
                changesDict[len(changesDict)+1] = (table_name, prev, new)
                break


def get_primary_key(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    for column in columns:
        if column[5]:
            return column[1]
    return None

def changeAulaTurma(ProjectNumber, idAula, idTurma):
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/duplicate_initial_database.db', check_same_thread=False)
    cursor = conn.cursor()
    stmt = '''UPDATE aulaTurmas SET idTurma=? WHERE idAula=?'''
    cursor.execute(stmt, (idTurma, idAula))
    conn.commit()

def changeAula(ProjectNumber, aula):
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/duplicate_initial_database.db', check_same_thread=False)
    cursor = conn.cursor()
    stmt = '''UPDATE aula SET horaInicial=?, duracao=?, diaSemana=?, teorico=?, semanaInicial=?, semanaFinal=? WHERE id=?'''
    cursor.execute(stmt, (aula["horaInicial"], aula["duracao"], aula["diaSemana"], aula["teorico"], aula["semanaInicial"], aula["semanaFinal"], aula["id"]))
    conn.commit()

def changeAulaSala(ProjectNumber, idAula, idSala):
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/duplicate_initial_database.db', check_same_thread=False)
    cursor = conn.cursor()
    stmt = '''UPDATE aulaSala SET idSala=? WHERE idAula=?'''
    cursor.execute(stmt, (idSala, idAula))
    conn.commit()

def changeAulaDocente(ProjectNumber, idAula, idDocente):
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/duplicate_initial_database.db', check_same_thread=False)
    cursor = conn.cursor()
    stmt = '''UPDATE aulaDocente SET idDocente=? WHERE idAula=?'''
    cursor.execute(stmt, (idDocente, idAula))
    conn.commit()

def switch_day_to_number(day_string):
    switch_dict = {
        'Segunda' : '0',
        'Terça' : '1',
        'Quarta' : '2',
        'Quinta' : '3',
        'Sexta' : '4',
        'Sábado' : '5'
    }
    return switch_dict.get(day_string, None)

def getAulaDiaHora(ProjectNumber, aulaId):
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/duplicate_initial_database.db', check_same_thread=False)
    conn.row_factory=sqlite3.Row
    cursor = conn.cursor()
    stmt = "SELECT * FROM aula WHERE id=?"
    cursor.execute(stmt, (aulaId,))
    aulaRow = cursor.fetchone()
    dia = aulaRow["diaSemana"]
    hora = aulaRow["horaInicial"]
    return dia, hora

def applyChangeToDB(ProjectNumber, table, new):
    conflicts = []

    if table == "aulaTurmas":
        changeAulaTurma(ProjectNumber, new["idAula"], new["idTurma"])
        diaAula, horaAula = getAulaDiaHora(ProjectNumber, new["idAula"])
        aulaId = new["idAula"]
        # print("diaAula: ", diaAula, " horaAula: ", horaAula, " aulaId: ", aulaId)
        conflicts = findAnyConflicts(ProjectNumber, diaAula, horaAula, aulaId)
        #print("conflicts: ", conflicts, "\n")

    elif table == "aula":
        changeAula(ProjectNumber, new)
        diaAula = new["diaSemana"]
        horaAula = new["horaInicial"]
        aulaId = new["id"]
        # print("diaAula: ", diaAula, " horaAula: ", horaAula, " aulaId: ", aulaId)
        conflicts = findAnyConflicts(ProjectNumber, diaAula, horaAula, aulaId)
        #print("conflicts: ", conflicts, "\n")

    elif table == "aulaSala":
        changeAulaSala(ProjectNumber, new["idAula"], new["idSala"])
        diaAula, horaAula = getAulaDiaHora(ProjectNumber, new["idAula"])
        aulaId = new["idAula"]
        # print("diaAula: ", diaAula, " horaAula: ", horaAula, " aulaId: ", aulaId)
        conflicts = findAnyConflicts(ProjectNumber, diaAula, horaAula, aulaId)
        #print("conflicts: ", conflicts, "\n")

    elif table == "aulaDocente":
        changeAulaDocente(ProjectNumber, new["idAula"], new["idDocente"])
        diaAula, horaAula = getAulaDiaHora(ProjectNumber, new["idAula"])
        aulaId = new["idAula"]
        # print("diaAula: ", diaAula, " horaAula: ", horaAula, " aulaId: ", aulaId)
        conflicts = findAnyConflicts(ProjectNumber, diaAula, horaAula, aulaId)
        #print("conflicts: ", conflicts, "\n")

    return conflicts

def generateConflicts(ProjectNumber, table, prev, new):
    print(f'{table} {prev} {new}')
    conflicts = applyChangeToDB(ProjectNumber, table, new)
    applyChangeToDB(ProjectNumber, table, prev)
    print("Conflicts next: ", conflicts)
    
    if len(conflicts) > 0:
        return True
    else:
        return False


def checkChangeToDB(ProjectNumber, generated_conflict, table, prev, new):
    print("Applying change to DB: ", new)
    new_conflicts = applyChangeToDB(ProjectNumber, table, new)

    if generated_conflict in new_conflicts:
        print("Change is NOT a solution\n")
        new_conflicts = applyChangeToDB(ProjectNumber, table, prev)
        print("New Conlficts", new_conflicts)
        return False, new_conflicts
    else:
        print("Change IS a solution\n")
        print("New Conlficts", new_conflicts)
        return True, new_conflicts

def findBestChange(ProjectNumber, changesDict, conflict, visited):
    print("Finding change for conflict: ", conflict)
    for change in changesDict:
        if change in visited:
            continue
        table, prev, new = changesDict[change]
        print("Checking if change", change, "is a solution...")
        solve_conflict, new_conflicts = checkChangeToDB(ProjectNumber, conflict, table, prev, new)
        if solve_conflict:
            return change, new_conflicts
    print("ERROR: No solution found for conflict: ", conflict)
    return None, None

def dfs_visit(ProjectNumber, changesDict, graph, change, visited):
    global changeOrder
    print("\n")
    print("Visiting change", change)
    print("Visited changes", visited)
    if change not in visited:
        table, prev, new = changesDict[change]
        visited.add(change)
        conflicts = applyChangeToDB(ProjectNumber, table, new)
        graph.add_node(change, table=table, prev=prev, new=new, order=changeOrder)
        changeOrder += 1
        print("Conflicts: ", conflicts)
        while len(conflicts) > 0:
            conflict = conflicts.pop(0)
            # find the next change that solves the conflict
            next_change, new_conflicts = findBestChange(ProjectNumber, changesDict, conflict, visited)
            table, prev, new = changesDict[next_change]
            graph.add_node(next_change, table=table, prev=prev, new=new, order=changeOrder)
            graph.add_edge(change, next_change)
            # print("New Conflicts: ", new_conflicts)
            # input("Press Enter to continue...")
            conflicts = dfs_visit(ProjectNumber, changesDict, graph, next_change, visited)
            # print("Conflicts: ", conflicts)
        return conflicts

# find all changes that do not generate any conflicts
# and put them as the first ones in the export graph
def findIndependentChanges(ProjectNumber, changesDict, visited, G):
    global changeOrder
    changeNum = 1
    while changeNum <= len(changesDict):
        table, prev, new = changesDict[changeNum]
        print("\nChange", changeNum)
        if changeNum not in visited and not generateConflicts(table, prev, new):
            applyChangeToDB(ProjectNumber, table, new)
            visited.add(changeNum)
            G.add_node(changeNum, table=table, prev=prev, new=new, order=changeOrder)
            changeOrder += 1
            changeNum = 1
            continue
        changeNum += 1

def buildExportGraph(ProjectNumber, changesDict):
    global changeOrder
    src = './database/Project' + str(ProjectNumber) + '/initial_database.db'
    dst = './database/Project' + str(ProjectNumber) + '/duplicate_initial_database.db'
    shutil.copy2(src, dst)

    duplicateInitialDB = sqlite3.connect(dst, check_same_thread=False)
    duplicateInitialDB.row_factory = sqlite3.Row

    queue = []
    for change in changesDict:
        table, prev, new = changesDict[change]
        queue.append((change, table, prev, new))

    # create a directed graph
    G = nx.DiGraph()
    visited = set()
    changeOrder = 1

    # findIndependentChanges(ProjectNumber, changesDict, visited, G)

    for change, table, prev, new in queue:
        # print(change, table, prev, new)
        print("For Loop", change)
        if change not in visited:
            dfs_visit(ProjectNumber, changesDict, G, change, visited)

    return G

def readGraph(ProjectNumber, graph, changesDict):
    nodes = graph.nodes(data=True)
    nodes = sorted(nodes, key=lambda x: x[1]['order'])
    
    visited = set()
    all_traversal_orders = []

    for node in [chg[0] for chg in nodes]:
        if node not in visited:
            stack = [node]
            traversal_order = []
            while stack:
                vertex = stack.pop()
                if vertex not in visited:
                    traversal_order.append(vertex)
                    visited.add(vertex)
                    stack.extend(reversed(list(graph.neighbors(vertex))))
            all_traversal_orders.append(traversal_order)
    
    functions = {
        "aulaSala": handleAulaSala,
        "docentes": handleDocentes,
        "salas": handleSalas,
        "aulaDocente": handleAulaDocente,
        "aula" : handleAulas, # Verificar se é necessário adicionar/remover aulas
        "aulaTurmas" : handleAulaTurmas,
        "aulaUC" : handleAulaUC
    }

    text = []
    for sequence in all_traversal_orders:
        current_uc = ""
        current_turma = ""
        for change in sequence:
            table = changesDict[change][0]
            prev = changesDict[change][1]
            new = changesDict[change][2]

            change_text = ""
            if table == "aula":
                idAula = new['id']
                info = getInformationFromAula(ProjectNumber, idAula)
                if current_uc=="":
                    text.append(f"em {info['uc_sigla']} ({info['uc_code']}):")
                    current_uc = info['uc_sigla']
                if current_turma=="":
                    text.append(f"Turma {info['turma']} ({prev['diaSemana']}, {str(prev['horaInicial'])[:-2] + ':' + str(prev['horaInicial'])[-2:]})")
                    current_turma = info['turma']

                text[-1] += f" -> ({new['diaSemana']}, {str(new['horaInicial'])[:-2] + ':' + str(new['horaInicial'])[-2:]})"
            
            elif table == "aulaSala":   
                idAula = new['idAula']
                info = getInformationFromAula(ProjectNumber, idAula)
                if current_uc=="":
                    text.append(f"em {info['uc_sigla']} ({info['uc_code']}):")
                    current_uc = info['uc_sigla']
                if current_turma=="":
                    text.append(f"Turma {info['turma']} ({info['dia']}, {str(info['hora'])[:-2] + ':' + str(info['hora'])[-2:]})")
                    current_turma = info['turma']
                    
                text[-1] += f" -> {new['idSala']}"
            
            elif table == "aulaDocente":
                idAula = new['idAula']
                info = getInformationFromAula(ProjectNumber, idAula)
                if current_uc=="":
                    text.append(f"em {info['uc_sigla']} ({info['uc_code']}):")
                    current_uc = info['uc_sigla']
                if current_turma=="":
                    text.append(f"Turma {info['turma']} ({info['dia']}, {str(info['hora'])[:-2] + ':' + str(info['hora'])[-2:]})")
                    current_turma = info['turma']

                docente = getAbreviacaoFromMecanografico(ProjectNumber, new['idDocente'])
                text[-1] += f" -> {docente}"
        text.append("")

    print(text)

    return text

def getDifferencesFromDatabases(ProjectNumber):
    changesDict = dict()
    
    functions = {
        "aulaSala": handleAulaSala,
        "docentes": handleDocentes,
        "salas": handleSalas,
        "aulaDocente": handleAulaDocente,
        "aula" : handleAulas, # Verificar se é necessário adicionar/remover aulas
        "aulaTurmas" : handleAulaTurmas,
        "aulaUC" : handleAulaUC
    }

    changesPerClass = {}
    path = "Project" + str(ProjectNumber)
    connDB = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    connDB.row_factory = sqlite3.Row
    cursorDB = connDB.cursor()
    connIni = sqlite3.connect('./database/' + path + '/initial_database.db', check_same_thread=False)
    connIni.row_factory = sqlite3.Row
    cursorIni = connIni.cursor()


    cursorDB.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables1 = cursorDB.fetchall()

    cursorIni.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables2 = cursorIni.fetchall()

    everyChange = []

    for table1 in tables1:

        table1_name = table1[0]

        for table2 in tables2:
            table2_name = table2[0]

            if table1_name == table2_name:
                # Compare table data
                cursorDB.execute(f"SELECT * FROM {table1_name};")
                data1 = cursorDB.fetchall()

                cursorDB.execute(f"PRAGMA table_info({table1_name});")
                columns1 = cursorDB.fetchall()

                cursorIni.execute(f"SELECT * FROM {table2_name};")
                data2 = cursorIni.fetchall()

                cursorIni.execute(f"PRAGMA table_info({table2_name});")
                columns2 = cursorIni.fetchall()

                set1 = set(data1)
                set2 = set(data2)

                if set1 != set2:
            
            
                    diff_data1 = set1 - set2
                    diff_data2 = set2 - set1

                    primaryKey = get_primary_key(connDB, table1_name)
                    addChangeToDict(changesDict, table1_name, primaryKey, diff_data1, diff_data2)

                    everyChange.append(functions[table1_name](set1, set2, ProjectNumber))
                    
                    
                    for row in diff_data1:
                    
                        for i in range(len(row)):
                            attribute_name = columns1[i][1]
                        
                    

                    for row in diff_data2:
                    
                        for i in range(len(row)):
                            attribute_name = columns2[i][1]
                        
                    
                break

    exportGraph = buildExportGraph(ProjectNumber, changesDict)

    formattedChanges = [item for sublist in everyChange for item in sublist]
    sortedChanges = sorted(formattedChanges, key=sortChanges)
    finalChanges = [string for precedence, string, id in sortedChanges]

    # printing the graph in a string
    graph_str = readGraph(ProjectNumber, exportGraph, changesDict)

    return graph_str

def globalChanges(ProjectNumber):
    changes = getDifferencesFromDatabases(ProjectNumber)
    with open("changes.txt", 'w') as file:
        for string in changes:
            file.write(f'=> {string}\n')
