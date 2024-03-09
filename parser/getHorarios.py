import sqlite3
from django.http import JsonResponse

def getDocenteHorario(ProjectNumber, numeroMecanografico): 
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('../database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    stmt = '''SELECT idAula FROM aulaDocente WHERE idDocente=?'''
    cursor.execute(stmt, (numeroMecanografico,))
    result = cursor.fetchall()
    list_of_results = []
              
    for row in result:
        if row['idAula'] is not None :
            stmt2 = '''SELECT * FROM aula WHERE id=?'''
            cursor.execute(stmt2, (row['idAula'],))
            newresult = cursor.fetchall()
            for row2 in newresult:
                list_of_results.append(row2)
    return list_of_results     

def getTurmaHorario(ProjectNumber, nomeTurma): 
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('../database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    stmt = '''SELECT idAula FROM aulaTurmas WHERE idTurma=?'''
    cursor.execute(stmt, (nomeTurma,))
    result = cursor.fetchall()
    list_of_results = []
              
    for row in result:
        if row['idAula'] is not None :
            stmt2 = '''SELECT * FROM aula WHERE id=?'''
            cursor.execute(stmt2, (row['idAula'],))
            newresult = cursor.fetchall()
            for row2 in newresult:
                list_of_results.append(row2)
    return list_of_results     

def getSalaHorario(ProjectNumber, numeroSala): 
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('../database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    stmt = '''SELECT idAula FROM aulaSala WHERE idSala=?'''
    cursor.execute(stmt, (numeroSala,))
    result = cursor.fetchall()
    list_of_results = []
              
    for row in result:
        if row['idAula'] is not None :
            stmt2 = '''SELECT * FROM aula WHERE id=?'''
            cursor.execute(stmt2, (row['idAula'],))
            newresult = cursor.fetchall()
            for row2 in newresult:
                list_of_results.append(row2)
    return list_of_results


def getUcHorario(ProjectNumber, codUc): 
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('../database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    stmt = '''SELECT idAula FROM aulaUC WHERE idUC=?'''
    cursor.execute(stmt, (codUc,))
    result = cursor.fetchall()
    list_of_results = []
              
    for row in result:
        if row['idAula'] is not None :
            stmt2 = '''SELECT * FROM aula WHERE id=?'''
            cursor.execute(stmt2, (row['idAula'],))
            newresult = cursor.fetchall()
            for row2 in newresult:
                list_of_results.append(row2)
    return list_of_results


def getDocenteBlocos(ProjectNumber, numeroMecanografico): 
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('../database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    stmt = '''SELECT idBloco FROM blocoDocente WHERE idDocente=?'''
    cursor.execute(stmt, (numeroMecanografico,))
    result = cursor.fetchall()
    list_of_results = []
              
    for row in result:
        if row['idBloco'] is not None :
            stmt2 = '''SELECT * FROM blocosVermelhos WHERE id=?'''
            cursor.execute(stmt2, (row['idBloco'],))
            newresult = cursor.fetchall()
            for row2 in newresult:
                list_of_results.append(row2)
    return list_of_results     

def getTurmaBlocos(ProjectNumber, numeroTurma): 
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('../database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    stmt = '''SELECT idBloco FROM blocoTurma WHERE idTurma=?'''
    cursor.execute(stmt, (numeroTurma,))
    result = cursor.fetchall()
    list_of_results = []
              
    for row in result:
        if row['idBloco'] is not None :
            stmt2 = '''SELECT * FROM blocosVermelhos WHERE id=?'''
            cursor.execute(stmt2, (row['idBloco'],))
            newresult = cursor.fetchall()
            for row2 in newresult:
                list_of_results.append(row2)
    return list_of_results  

def getSalaBlocos(ProjectNumber, numeroSala): 
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('../database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    stmt = '''SELECT idBloco FROM salaBloco WHERE idSala=?'''
    cursor.execute(stmt, (numeroSala,))
    result = cursor.fetchall()
    list_of_results = []
              
    for row in result:
        if row['idBloco'] is not None :
            stmt2 = '''SELECT * FROM blocosVermelhos WHERE id=?'''
            cursor.execute(stmt2, (row['idBloco'],))
            newresult = cursor.fetchall()
            for row2 in newresult:
                list_of_results.append(row2)
    return list_of_results  

def checkIfDocenteConflict(ProjectNumber, day, hour, idAula):
    manchaDocentes = {}
    listaConflitos = []
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('../database/' + path + '/general_database.db', check_same_thread=False)
    cursor = conn.cursor()
    stmt = '''SELECT idDocente FROM aulaDocente WHERE idAula=?'''
    cursor.execute(stmt, (idAula,))
    allDocentes = cursor.fetchall()
    for docente in allDocentes: 
        ocupacaoDocente = []
        horarioDocente = getDocenteHorario(ProjectNumber, docente[0])
        for entry in horarioDocente:
            duracao = entry['duracao']
            hora = entry['horaInicial']
            while duracao >= 1:
                ocupacaoDocente.append((hora, entry['diaSemana']))
                hora += 30
                if hora % 100 == 60:
                    hora += 40
                duracao -= 1
            
        blocosDocente = getDocenteBlocos(ProjectNumber, docente[0])
        for entry in blocosDocente:
            ocupacaoDocente.append((entry['hora'], entry['diaSemana']))
        
        manchaDocentes[docente] = ocupacaoDocente
    for docente in manchaDocentes:
        if (hour,day) in manchaDocentes[docente]:
            listaConflitos.append(docente[0])

    if (len(listaConflitos) == 0):
        return "Aula is moveable"
        #return JsonResponse({"id": idAula}, status=200)
    else:
        mensagemErro = "Docentes "
        for docente in listaConflitos:
            mensagemErro += docente + ","
        mensagemErro = mensagemErro.rstrip(",")
        mensagemErro += " are occupied"
        return mensagemErro
        #return JsonResponse({"id": idAula, "erro":mensagemErro}, status=400)

def checkIfTurmaConflict(ProjectNumber, day, hour, idAula):
    manchaTurma = {}
    listaConflitos = []
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('../database/' + path + '/general_database.db', check_same_thread=False)
    cursor = conn.cursor()
    stmt = '''SELECT idTurma FROM aulaTurmas WHERE idAula=?'''
    cursor.execute(stmt, (idAula,))
    allTurmas = cursor.fetchall()
    for turma in allTurmas: 
        ocupacaoTurma = []
        horarioTurma = getTurmaHorario(ProjectNumber, turma[0])
        for entry in horarioTurma:
            duracao = entry['duracao']
            hora = entry['horaInicial']
            while duracao >= 1:
                ocupacaoTurma.append((hora, entry['diaSemana']))
                hora += 30
                if hora % 100 == 60:
                    hora += 40
                duracao -= 1
            
        blocosTurma = getTurmaBlocos(ProjectNumber, turma[0])
        for entry in blocosTurma:
            ocupacaoTurma.append((entry['hora'], entry['diaSemana']))
        
        manchaTurma[turma] = ocupacaoTurma
    for turma in manchaTurma:
        if (hour,day) in manchaTurma[turma]:
            listaConflitos.append(turma[0])

    if (len(listaConflitos) == 0):
        return "Aula is moveable"
        #return JsonResponse({"id": idAula}, status=200)
    else:
        mensagemErro = "Turmas "
        for turma in listaConflitos:
            mensagemErro += turma + ", "
        mensagemErro = mensagemErro.rstrip(", ")
        mensagemErro += " are occupied"
        return mensagemErro
        #return JsonResponse({"id": idAula, "erro":mensagemErro}, status=400)

def checkIfUCConflict(ProjectNumber, day, hour, idAula):
    manchaUC = {}
    listaConflitos = []
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('../database/' + path + '/general_database.db', check_same_thread=False)
    cursor = conn.cursor()
    stmt = '''SELECT idUC FROM aulaUC WHERE idAula=?'''
    cursor.execute(stmt, (idAula,))
    allUC = cursor.fetchall()
    for uc in allUC: 
        ocupacaoUC = []
        horarioUC = getUcHorario(ProjectNumber, uc[0])
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
        if (hour,day) in manchaUC[uc]:
            listaConflitos.append(uc[0])

    if (len(listaConflitos) == 0):
        return "Aula is moveable"
        #return JsonResponse({"id": idAula}, status=200)
    else:
        mensagemErro = "UCs "
        for uc in listaConflitos:
            mensagemErro += uc + ", "
        mensagemErro = mensagemErro.rstrip(", ")
        mensagemErro += " are occupied"
        return mensagemErro
        #return JsonResponse({"id": idAula, "erro":mensagemErro}, status=400)

def checkIfSalaConflict(ProjectNumber, day, hour, idAula):
    manchasala = {}
    listaConflitos = []
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('../database/' + path + '/general_database.db', check_same_thread=False)
    cursor = conn.cursor()
    stmt = '''SELECT idSala FROM aulaSala WHERE idAula=?'''
    cursor.execute(stmt, (idAula,))
    allSala = cursor.fetchall()
    for sala in allSala: 
        ocupacaosala = []
        horariosala = getSalaHorario(ProjectNumber, sala[0])
        for entry in horariosala:
            duracao = entry['duracao']
            hora = entry['horaInicial']
            while duracao >= 1:
                ocupacaosala.append((hora, entry['diaSemana']))
                hora += 30
                if hora % 100 == 60:
                    hora += 40
                duracao -= 1
                    
        blocossala = getSalaBlocos(ProjectNumber, sala[0])
        for entry in blocossala:
            ocupacaosala.append((entry['hora'], entry['diaSemana']))

        manchasala[sala] = ocupacaosala

        
    for uc in manchasala:
        if (hour,day) in manchasala[sala]:
            listaConflitos.append(sala[0])

    if (len(listaConflitos) == 0):
        return "Aula is moveable"
        #return JsonResponse({"id": idAula}, status=200)
    else:
        mensagemErro = "Salas "
        for sala in listaConflitos:
            mensagemErro += sala + ", "
        mensagemErro = mensagemErro.rstrip(", ")
        mensagemErro += " are occupied"
        return mensagemErro
        #return JsonResponse({"id": idAula, "erro":mensagemErro}, status=400)


def findAnyConflicts(ProjectNumber, day, hour, idAula):
    conflitos = []
    if checkIfDocenteConflict(ProjectNumber, day, hour, idAula) != "Aula is moveable":
        conflitos.append(checkIfDocenteConflict(ProjectNumber, day, hour, idAula))
    if checkIfSalaConflict(ProjectNumber, day, hour, idAula) != "Aula is moveable":
        conflitos.append(checkIfSalaConflict(ProjectNumber, day, hour, idAula))
    if checkIfTurmaConflict(ProjectNumber, day, hour, idAula) != "Aula is moveable":
        conflitos.append(checkIfTurmaConflict(ProjectNumber, day, hour, idAula))
    if checkIfUCConflict(ProjectNumber, day, hour, idAula) != "Aula is moveable":
        conflitos.append(checkIfUCConflict(ProjectNumber, day, hour, idAula))

    if len(conflitos)==0:
        return []
    else:
        return conflitos
    

def addDocente(ProjectNumber, idAula, novoDocente):
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('../database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory=sqlite3.Row
    cursor = conn.cursor()
    stmt = '''SELECT * from aula WHERE id=?'''
    cursor.execute(stmt, (idAula,))
    result = cursor.fetchall()
    hour = result[0]['horaInicial']
    day = result[0]['diaSemana']    
    ocupacaoDocente = []
    horarioDocente = getDocenteHorario(ProjectNumber, novoDocente)
    for entry in horarioDocente:
        duracao = entry['duracao']
        hora = entry['horaInicial']
        while duracao >= 1:
            ocupacaoDocente.append((hora, entry['diaSemana']))
            hora += 30
            if hora % 100 == 60:
                hora += 40
            duracao -= 1
        
    blocosDocente = getDocenteBlocos(ProjectNumber, novoDocente)
    for entry in blocosDocente:
        ocupacaoDocente.append((entry['hora'], entry['diaSemana']))
    print(ocupacaoDocente)
    if (hour,day) in ocupacaoDocente:
        print("Not possible")
    else:
        stmt2 = '''INSERT INTO aulaDocente (idAula, idDocente) VALUES (?,?)'''
        cursor.execute(stmt2, (idAula, novoDocente,)) 
        conn.commit()
        print("Added")
# add returns


def removeDocente(ProjectNumber, idAula, docenteToRemove):
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('../database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory=sqlite3.Row
    cursor = conn.cursor()
    stmt = '''SELECT * FROM aulaDocente WHERE idDocente=?'''
    cursor.execute(stmt, (docenteToRemove,))
    result = cursor.fetchall()
    for aula in result:
        if idAula in aula:
            stmtRemove = '''DELETE FROM aulaDocente WHERE idAula=? AND idDocente=?'''
            cursor.execute(stmtRemove, (idAula,docenteToRemove))
    conn.commit()
# add returns

def switchDocentes(ProjectNumber, idAula, docenteToRemove, docenteToAdd):
    removeDocente(ProjectNumber, idAula, docenteToRemove)
    addDocente(ProjectNumber, idAula, docenteToAdd)


def addSala(ProjectNumber, idAula, novaSala):
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('../database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory=sqlite3.Row
    cursor = conn.cursor()
    stmt = '''INSERT INTO aulaSala (idAula, idSala) VALUES (?, ?)'''
    cursor.execute(stmt, (idAula, novaSala))
    conn.commit()
        
def removeSala(ProjectNumber, idAula, salaToRemove):
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('../database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory=sqlite3.Row
    cursor = conn.cursor()
    stmt = '''DELETE FROM aulaSala WHERE idAula=? AND idSala=?'''
    cursor.execute(stmt, (idAula, salaToRemove))
    conn.commit()

def switchSalas(ProjectNumber, idAula, novaSala, salaToRemove):
    addSala(ProjectNumber, idAula, novaSala)
    removeSala(ProjectNumber, idAula, salaToRemove)



def getAulasFromTurno(ProjectNumber, turno):
    manchaTurmas = {} 
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('../database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory=sqlite3.Row
    cursor = conn.cursor()
    stmt = '''SELECT idTurma from turno WHERE numero=?'''
    cursor.execute(stmt, (turno,))
    result = cursor.fetchall()
    for turma in result:
        ocupacaoTurma = []
        horarioTurma = getTurmaHorario(ProjectNumber, turma['idTurma'])
        for elem in horarioTurma:
            ocupacaoTurma.append((elem['horaInicial'],elem['diaSemana']))
        manchaTurmas[turma['idTurma']] = ocupacaoTurma
    print(manchaTurmas)

def getAulasByTipoSala(ProjectNumber):
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('../database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory=sqlite3.Row
    cursor = conn.cursor()
    stmt = '''SELECT s.tipo || ' : ' || a.diaSemana || ' : ' || COUNT(*) AS resultado FROM aula as a JOIN aulaSala AS ASL ON a.id = ASL.idAula JOIN salas AS s ON ASL.idSala = s.numero GROUP BY s.tipo, a.diaSemana;'''
    cursor.execute(stmt)
    results = cursor.fetchall()
    sala_dict = {}
    for row in results:
        tipo_sala, dia_semana, contagem = row[0].split(' : ')
        if tipo_sala not in sala_dict:
            sala_dict[tipo_sala] = {}
        sala_dict[tipo_sala][dia_semana] = int(contagem)



