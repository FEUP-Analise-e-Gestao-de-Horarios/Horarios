import sqlite3
import getHorariosFromDB.conflictFunctions as conf
import getHorariosFromDB.auxiliaryScheduleFunctions as aux

def addDocente(ProjectNumber, idAula, novoDocente):
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory=sqlite3.Row
    cursor = conn.cursor()
    stmt = '''SELECT * from aula WHERE id=?'''
    cursor.execute(stmt, (idAula,))
    result = cursor.fetchall()
    hour = result[0]['horaInicial']
    day = result[0]['diaSemana']    
    ocupacaoDocente = []
    horarioDocente = aux.getDocenteHorario(ProjectNumber, novoDocente)
    for entry in horarioDocente:
        duracao = entry['duracao']
        hora = entry['horaInicial']
        while duracao >= 1:
            ocupacaoDocente.append((hora, entry['diaSemana']))
            hora += 30
            if hora % 100 == 60:
                hora += 40
            duracao -= 1
        
    blocosDocente = aux.getDocenteBlocos(ProjectNumber, novoDocente)
    for entry in blocosDocente:
        ocupacaoDocente.append((entry['hora'], entry['diaSemana']))
    stmt2 = '''INSERT INTO aulaDocente (idAula, idDocente) VALUES (?,?)'''
    cursor.execute(stmt2, (idAula, novoDocente,)) 
    conn.commit()
    print("Added")
    return 0
# add returns


def removeDocente(ProjectNumber, idAula, docenteToRemove):
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory=sqlite3.Row
    cursor = conn.cursor()
    stmt='''DELETE FROM aulaDocente WHERE idAula=? AND idDocente =?'''
    cursor.execute(stmt, (idAula, docenteToRemove))
    conn.commit()
# add returns

def switchDocentes(ProjectNumber, idAula, docenteToRemove, docenteToAdd):
    removeDocente(ProjectNumber, idAula, docenteToRemove)
    addDocente(ProjectNumber, idAula, docenteToAdd)

def addSala(ProjectNumber, idAula, novaSala):
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory=sqlite3.Row
    cursor = conn.cursor()
    stmt = '''INSERT INTO aulaSala (idAula, idSala) VALUES (?, ?)'''
    cursor.execute(stmt, (idAula, novaSala))
    conn.commit()
        
def removeSala(ProjectNumber, idAula, salaToRemove):
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory=sqlite3.Row
    cursor = conn.cursor()
    stmt = '''DELETE FROM aulaSala WHERE idAula=? AND idSala=?'''
    cursor.execute(stmt, (idAula, salaToRemove))
    conn.commit()

def switchSalas(ProjectNumber, idAula, novaSala, salaToRemove):
    addSala(ProjectNumber, idAula, novaSala)
    removeSala(ProjectNumber, idAula, salaToRemove)

def moveAula(ProjectNumber, idAula, day, hour):
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory=sqlite3.Row
    cursor = conn.cursor()
    stmt = '''UPDATE aula SET diaSemana=?, horaInicial=? WHERE id=?'''
    cursor.execute(stmt, (day, hour, idAula,))
    conn.commit()

def switchAulas(ProjectNumber, idAula1, idAula2):
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory=sqlite3.Row
    cursor = conn.cursor()
    stmt = "SELECT * FROM aula WHERE id=?"
    cursor.execute(stmt, (idAula1,))
    aula1Row = cursor.fetchAll()
    cursor.execute(stmt, (idAula2,))
    aula2Row = cursor.fetchAll()
    dia1 = aula1Row["diaSemana"]
    hora1 = aula1Row["horaInicial"]
    dia2 = aula2Row["diaSemana"]
    hora2 = aula2Row["horaInicial"]
    moveAula(ProjectNumber, idAula1, dia2, hora2)
    moveAula(ProjectNumber, idAula2, dia1, hora1)


def changeUC(ProjectNumber, idAula, idUC):
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    cursor = conn.cursor()
    stmt = '''UPDATE aulaUC SET idUC=? WHERE idAula=?'''
    cursor.execute(stmt, (idUC, idAula))
    conn.commit()

def updateAulaDuration(ProjectNumber, idAula, duracao):
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    cursor = conn.cursor()
    stmt = '''UPDATE aula SET duracao = ? WHERE id=?'''
    cursor.execute(stmt, (duracao, idAula))
    conn.commit()

def addTurma(ProjectNumber, idAula, novaTurma):
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory=sqlite3.Row
    cursor = conn.cursor()
    stmt = '''INSERT INTO aulaTurmas (idAula, idTurma) VALUES (?, ?)'''
    cursor.execute(stmt, (idAula, novaTurma))
    conn.commit()
    print(f'error in addTurma with ProjectNumber: {ProjectNumber}, idAula: {idAula}, idTurma: {novaTurma}')

def removeTurma(ProjectNumber, idAula, turmaToRemove):
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory=sqlite3.Row
    cursor = conn.cursor()
    stmt = '''DELETE FROM aulaTurmas WHERE idAula=? AND idTurma=?'''
    cursor.execute(stmt, (idAula, turmaToRemove))
    conn.commit()
