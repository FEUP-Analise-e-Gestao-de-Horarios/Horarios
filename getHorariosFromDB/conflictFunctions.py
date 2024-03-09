import sqlite3, json, os
import getHorariosFromDB.graph as graph_controller
import getHorariosFromDB.auxiliaryScheduleFunctions as aux
import sqlite3

def converter_horario(num):
    hora, minuto = divmod(num, 100)
    return f"{hora:02d}:{minuto:02d}"   

def checkIfDocenteConflict(ProjectNumber, day, hour, idAula):
    manchaDocentes = {}
    listaConflitos = {}
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    cursor = conn.cursor()
    stmt = '''SELECT idDocente FROM aulaDocente WHERE idAula=?'''
    cursor.execute(stmt, (idAula,))
    allDocentes = cursor.fetchall()
    tupleAulas = (idAula, 0)
    for docente in allDocentes: 
        ocupacaoDocente = []
        horarioDocente = aux.getDocenteHorario(ProjectNumber, docente[0])
        for entry in horarioDocente:
            duracao = entry['duracao']
            hora = entry['horaInicial']
            while duracao >= 1:
                ocupacaoDocente.append((hora, entry['diaSemana']))
                hora += 30
                if hora % 100 == 60:
                    hora += 40
                duracao -= 1
            
        blocosDocente = aux.getDocenteBlocos(ProjectNumber, docente[0])
        for entry in blocosDocente:
            ocupacaoDocente.append((entry['hora'], entry['diaSemana']))
        manchaDocentes[docente] = ocupacaoDocente
    for docente in manchaDocentes:
        hourDay = (int(hour), day)
        if (hourDay in manchaDocentes[docente]):
            listaAulas = aux.getAulaFromDocenteAndTime(ProjectNumber, int(hour), day, docente[0], idAula)
            if (listaAulas is not None):
                if (int(len(listaAulas)) >= 1): # mais de uma aula: conflitos
                    if (listaAulas[0] != -1):
                        everyConflict = []
                        for i in listaAulas:
                            tupleAula = (int(idAula), int(i))
                            everyConflict.append(tupleAula)
                        listaConflitos[docente[0]] = everyConflict
                    else:
                        listaConflitos[docente[0]] = [(int(idAula), int(idAula))]    
    graph_controller.handle_conflict_of_same_aulas(ProjectNumber, tupleAulas[0], "Docente")
    print(f"Docente Lista de Conflitos {listaConflitos}")
    if (len(listaConflitos)!=0):
        mensagensErro = []
        for docente in listaConflitos:
            mensagemErro = "Docente " + aux.getAbreviacaoFromMecanografico(ProjectNumber, docente) + " está ocupado"
            mensagensErro.append(mensagemErro)
    
            for conflito in listaConflitos[docente]:
                graph_controller.add_node_to_graph(ProjectNumber, conflito[0])
                graph_controller.add_node_to_graph(ProjectNumber, conflito[1])
                graph_controller.add_edge_to_graph(ProjectNumber, conflito[0], conflito[1], mensagemErro)

        
            

def checkIfTurmaConflict(ProjectNumber, day, hour, idAula):
    manchaTurma = {}
    listaConflitos = {}
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    cursor = conn.cursor()
    stmt = '''SELECT idTurma FROM aulaTurmas WHERE idAula=?'''
    cursor.execute(stmt, (idAula,))
    allTurmas = cursor.fetchall()
    tupleAulas = (idAula, 0)
    for turma in allTurmas: 
        ocupacaoTurma = []
        horarioTurma = aux.getTurmaHorario(ProjectNumber, turma[0])
        for entry in horarioTurma:
            duracao = entry['duracao']
            hora = entry['horaInicial']
            while duracao >= 1:
                ocupacaoTurma.append((hora, entry['diaSemana']))
                hora += 30
                if hora % 100 == 60:
                    hora += 40
                duracao -= 1
            
        blocosTurma = aux.getTurmaBlocos(ProjectNumber, turma[0])
        for entry in blocosTurma:
            ocupacaoTurma.append((entry['hora'], entry['diaSemana']))
        
        manchaTurma[turma] = ocupacaoTurma
    for turma in manchaTurma:
        hourDay = (int(hour), day)
        if (hourDay in manchaTurma[turma]):
            listaAulas = aux.getAulaFromTurmaAndTime(ProjectNumber, int(hour), day, turma[0], idAula)
            if (listaAulas is not None):
                if (int(len(listaAulas)) >= 1): # mais de uma aula: conflitos
                    if (listaAulas[0] != -1):
                        everyConflict = []
                        for i in listaAulas:
                            tupleAula = (int(idAula), int(i))
                            everyConflict.append(tupleAula)
                        listaConflitos[turma[0]] = everyConflict
                    else:
                        listaConflitos[turma[0]] = [(int(idAula), int(idAula))]    
    graph_controller.handle_conflict_of_same_aulas(ProjectNumber, tupleAulas[0], "Turma")
    if (len(listaConflitos)!=0):
        mensagensErro = []
        for turma in listaConflitos:
            mensagemErro = "Turma " + turma + " está ocupada"
            mensagensErro.append(mensagemErro)
    
            for conflito in listaConflitos[turma]:
                graph_controller.add_node_to_graph(ProjectNumber, conflito[0])
                graph_controller.add_node_to_graph(ProjectNumber, conflito[1])
                graph_controller.add_edge_to_graph(ProjectNumber, conflito[0], conflito[1], mensagemErro)


def checkIfUCConflict(ProjectNumber, day, hour, idAula):
    manchaUC = {}
    listaConflitos = {}
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    cursor = conn.cursor()
    stmt = '''SELECT idUC FROM aulaUC WHERE idAula=?'''
    cursor.execute(stmt, (idAula,))
    allUC = cursor.fetchall()
    tupleAulas = (idAula, 0)
    for uc in allUC: 
        ocupacaoUC = []
        horarioUC = aux.getUcHorario(ProjectNumber, uc[0])
        for entry in horarioUC:
            duracao = entry['duracao']
            hora = entry['horaInicial']
            while duracao >= 1:
                ocupacaoUC.append((hora, entry['diaSemana']))
                hora += 30
                if hora % 100 == 60:
                    hora += 40
                duracao -= 1
                    
        manchaUC[uc] = ocupacaoUC
    for uc in manchaUC:
        hourDay = (int(hour), day)
        if (hourDay in manchaUC[uc]):
            listaAulas = aux.getAulaFromUCAndTime(ProjectNumber, int(hour), day, uc[0], idAula)
            if (listaAulas is not None):
                if (int(len(listaAulas)) >= 1): # mais de uma aula: conflitos
                    if (listaAulas[0] != -1):
                        everyConflict = []
                        for i in listaAulas:
                            tupleAula = (int(idAula), int(i))
                            everyConflict.append(tupleAula)
                        listaConflitos[uc[0]] = everyConflict
                    else:
                        listaConflitos[uc[0]] = [(int(idAula), int(idAula))]    
    graph_controller.handle_conflict_of_same_aulas(ProjectNumber, tupleAulas[0], "Uc")
    if (len(listaConflitos)!=0):
        mensagensErro = []
        for uc in listaConflitos:
            mensagemErro = "UC " + uc + " está ocupada"
            mensagensErro.append(mensagemErro)
    
            for conflito in listaConflitos[uc]:
                graph_controller.add_node_to_graph(ProjectNumber, conflito[0])
                graph_controller.add_node_to_graph(ProjectNumber, conflito[1])
                graph_controller.add_edge_to_graph(ProjectNumber, conflito[0], conflito[1], mensagemErro)


def checkIfSalaConflict(ProjectNumber, day, hour, idAula):
    manchasala = {}
    listaConflitos = {}
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    cursor = conn.cursor()
    stmt = '''SELECT idSala FROM aulaSala WHERE idAula=?'''
    cursor.execute(stmt, (idAula,))
    allSala = cursor.fetchall()
    tupleAulas = (idAula, 0)
    for sala in allSala: 
        ocupacaosala = []
        horariosala = aux.getSalaHorario(ProjectNumber, sala[0])
        for entry in horariosala:
            duracao = entry['duracao']
            hora = entry['horaInicial']
            while duracao >= 1:
                ocupacaosala.append((hora, entry['diaSemana']))
                hora += 30
                if hora % 100 == 60:
                    hora += 40
                duracao -= 1
                    
        blocossala = aux.getSalaBlocos(ProjectNumber, sala[0])
        for entry in blocossala:
            ocupacaosala.append((entry['hora'], entry['diaSemana']))

        manchasala[sala] = ocupacaosala

    for sala in manchasala:
        hourDay = (int(hour), day)
        if (hourDay in manchasala[sala]):
            listaAulas = aux.getAulaFromSalaAndTime(ProjectNumber, int(hour), day, sala[0], idAula)
            if (listaAulas is not None):
                if (int(len(listaAulas)) >= 1): # mais de uma aula: conflitos
                    if (listaAulas[0] != -1):
                        everyConflict = []
                        for i in listaAulas:
                            tupleAula = (int(idAula), int(i))
                            everyConflict.append(tupleAula)
                        listaConflitos[sala[0]] = everyConflict
                    else:
                        listaConflitos[sala[0]] = [(int(idAula), int(idAula))]    
            #verify this!
    
    graph_controller.handle_conflict_of_same_aulas(ProjectNumber, tupleAulas[0], "Sala")
    if (len(listaConflitos)!=0):
        mensagensErro = []
        for sala in listaConflitos:
            mensagemErro = "Sala " + sala + " está ocupada"
            mensagensErro.append(mensagemErro)
    
            for conflito in listaConflitos[sala]:
                graph_controller.add_node_to_graph(ProjectNumber, conflito[0])
                graph_controller.add_node_to_graph(ProjectNumber, conflito[1])
                graph_controller.add_edge_to_graph(ProjectNumber, conflito[0], conflito[1], mensagemErro)



def organizeInformation(ProjectNumber, conflicts):
    confList = []
    formatting = "Aula {} ({} - {} [Turma: {}]) / Aula {} ({} - {} [Turma: {}]) : {}"
    formatForSameAula = "Aula {} ({} - {} [Turma: {}]) : Período de Indisponibilidade: {}"
    path = "Project" + str(ProjectNumber)
    file_path = './database/' + path + '/conflicts_text.txt'
    with open(file_path, 'w') as file:
        for aulas in conflicts:
            informationAula1 = aux.getInformationFromAula(ProjectNumber, aulas[0])
            informationAula2 = aux.getInformationFromAula(ProjectNumber, aulas[1])
            if (informationAula1==informationAula2):
                resultString = formatForSameAula.format(informationAula1[2], informationAula1[1], converter_horario(informationAula1[0]), informationAula1[3], conflicts[aulas])
            else:
                resultString = formatting.format(informationAula1[2], informationAula1[1], converter_horario(informationAula1[0]), informationAula1[3], informationAula2[2], informationAula2[1], converter_horario(informationAula2[0]), informationAula2[3], conflicts[aulas])
            confList.append(resultString)
            file.write(resultString + "\n")
    return confList


def findAnyConflicts(ProjectNumber, day, hour, idAula):
    graph_controller.init_graph(ProjectNumber)
    checkIfDocenteConflict(ProjectNumber, day, hour, idAula)
    conflicts = graph_controller.get_organized_conflicts(ProjectNumber)
    checkIfSalaConflict(ProjectNumber, day, hour, idAula)
    checkIfTurmaConflict(ProjectNumber, day, hour, idAula)
    #checkIfUCConflict(ProjectNumber, day, hour, idAula)
    graph_controller.clean_graph(ProjectNumber)
    conflicts = graph_controller.get_organized_conflicts(ProjectNumber)
    return organizeInformation(ProjectNumber, conflicts)

