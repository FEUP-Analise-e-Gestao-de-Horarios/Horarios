from comparingDatabases import handleAulaSala
from comparingDatabases import handleDocentes
from comparingDatabases import handleSalas
from comparingDatabases import handleAulaDocente
from comparingDatabases import handleAulas
from comparingDatabases import handleAulaTurmas
from comparingDatabases import handleAulaUC
from comparingDatabases import sortChanges
from conflictFunctionsDup import findAnyConflicts
import sqlite3
import networkx as nx
import matplotlib.pyplot as plt
from itertools import groupby
import shutil
import os

projectNumber = 23

def getDifferencesFromDatabases(ProjectNumber):
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
                    addChangeToDict(table1_name, primaryKey, diff_data1, diff_data2)
            
                    everyChange.append(functions[table1_name](set1, set2, ProjectNumber))
                    
                    
                    for row in diff_data1:
                    
                        for i in range(len(row)):
                            attribute_name = columns1[i][1]
                        
                    

                    for row in diff_data2:
                    
                        for i in range(len(row)):
                            attribute_name = columns2[i][1]
                        
                    
                break

    # print("everychange: ", everyChange)
    formattedChanges = [item for sublist in everyChange for item in sublist]
    sortedChanges = sorted(formattedChanges, key=sortChanges)
    finalChanges = [string for precedence, string, id in sortedChanges]
    return finalChanges  

# declare a pair
# number of change : (table name, {previous data}, {new data}})
changesDict = {0:("",{},{})}

def addChangeToDict(table_name, primaryKey, diff_data1, diff_data2):
    # print("Table: ", table_name)
    # print("Primary Key: ", primaryKey)

    new_changes = [dict(row) for row in diff_data1]
    prev_changes = [dict(row) for row in diff_data2]

    for prev in prev_changes:
        for new in new_changes:
            if prev[primaryKey] == new[primaryKey]:
                changesDict[len(changesDict)] = (table_name, prev, new)
                break


def get_primary_key(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    for column in columns:
        if column[5]:
            return column[1]
    return None

def switchAulas(ProjectNumber, idAula1, idAula2):
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/duplicate_initial_database.db', check_same_thread=False)
    conn.row_factory=sqlite3.Row
    cursor = conn.cursor()
    stmt = "SELECT * FROM aula WHERE id=?"
    cursor.execute(stmt, (idAula1,))
    aula1Row = cursor.fetchone()
    cursor.execute(stmt, (idAula2,))
    aula2Row = cursor.fetchone()
    
    dia1 = aula1Row["diaSemana"]
    hora1 = aula1Row["horaInicial"]
    dia2 = aula2Row["diaSemana"]
    hora2 = aula2Row["horaInicial"]

    moveAula(ProjectNumber, idAula1, dia2, hora2)
    moveAula(ProjectNumber, idAula2, dia1, hora1)

def moveAula(ProjectNumber, idAula, day, hour):
    # print("moveAula: aulaId:", idAula, " day:", day, " hour:", hour)
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/duplicate_initial_database.db', check_same_thread=False)
    conn.row_factory=sqlite3.Row
    cursor = conn.cursor()
    stmt = '''UPDATE aula SET diaSemana=?, horaInicial=? WHERE id=?'''
    cursor.execute(stmt, (day, hour, idAula,))
    conn.commit()

def changeAulaTurma(ProjectNumber, idAula, idTurma):
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/duplicate_initial_database.db', check_same_thread=False)
    cursor = conn.cursor()
    stmt = '''UPDATE aulaTurmas SET idTurma=? WHERE idAula=?'''
    cursor.execute(stmt, (idTurma, idAula))
    conn.commit()


# 1 aula {'id': 784, 'horaInicial': 830, 'duracao': 4, 'diaSemana': 'Terça', 'teorico': 0, 'semanaInicial': '2024-02-05', 'semanaFinal': '2024-05-20'} {'id': 784, 'horaInicial': 1030, 'duracao': 4, 'diaSemana': 'Segunda', 'teorico': 0, 'semanaInicial': '2024-02-05', 'semanaFinal': '2024-05-20'}
# 2 aula {'id': 817, 'horaInicial': 1030, 'duracao': 4, 'diaSemana': 'Segunda', 'teorico': 0, 'semanaInicial': '2024-02-05', 'semanaFinal': '2024-05-20'} {'id': 817, 'horaInicial': 830, 'duracao': 4, 'diaSemana': 'Terça', 'teorico': 0, 'semanaInicial': '2024-02-05', 'semanaFinal': '2024-05-20'}
# 3 aulaSala {'idAula': 817, 'idSala': 'B219'} {'idAula': 817, 'idSala': 'B334'}
# 4 aulaSala {'idAula': 784, 'idSala': 'B334'} {'idAula': 784, 'idSala': 'B219'}

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

def getAulaDiaHora(aulaId):
    path = "Project"+str(projectNumber)
    conn = sqlite3.connect('./database/' + path + '/duplicate_initial_database.db', check_same_thread=False)
    conn.row_factory=sqlite3.Row
    cursor = conn.cursor()
    stmt = "SELECT * FROM aula WHERE id=?"
    cursor.execute(stmt, (aulaId,))
    aulaRow = cursor.fetchone()
    dia = aulaRow["diaSemana"]
    hora = aulaRow["horaInicial"]
    return dia, hora

def applyChangeToDB(table, new):
    conflicts = []

    if table == "aulaTurmas":
        changeAulaTurma(projectNumber, new["idAula"], new["idTurma"])
        diaAula, horaAula = getAulaDiaHora(new["idAula"])
        aulaId = new["idAula"]
        # print("diaAula: ", diaAula, " horaAula: ", horaAula, " aulaId: ", aulaId)
        conflicts = findAnyConflicts(projectNumber, diaAula, horaAula, aulaId)
        print("conflicts: ", conflicts, "\n")

    elif table == "aula":
        changeAula(projectNumber, new)
        diaAula = new["diaSemana"]
        horaAula = new["horaInicial"]
        aulaId = new["id"]
        # print("diaAula: ", diaAula, " horaAula: ", horaAula, " aulaId: ", aulaId)
        conflicts = findAnyConflicts(projectNumber, diaAula, horaAula, aulaId)
        print("conflicts: ", conflicts, "\n")

    elif table == "aulaSala":
        changeAulaSala(projectNumber, new["idAula"], new["idSala"])
        diaAula, horaAula = getAulaDiaHora(new["idAula"])
        aulaId = new["idAula"]
        # print("diaAula: ", diaAula, " horaAula: ", horaAula, " aulaId: ", aulaId)
        conflicts = findAnyConflicts(projectNumber, diaAula, horaAula, aulaId)
        print("conflicts: ", conflicts, "\n")

    elif table == "aulaDocente":
        changeAulaDocente(projectNumber, new["idAula"], new["idDocente"])
        diaAula, horaAula = getAulaDiaHora(new["idAula"])
        aulaId = new["idAula"]
        # print("diaAula: ", diaAula, " horaAula: ", horaAula, " aulaId: ", aulaId)
        conflicts = findAnyConflicts(projectNumber, diaAula, horaAula, aulaId)
        print("conflicts: ", conflicts, "\n")

    return conflicts

def checkChangeToDB(generated_conflict, table, prev, new):
    print("Applying change to DB: ", new)
    new_conflicts = applyChangeToDB(table, new)

    print("Checking if change is a solution...")
    if generated_conflict in new_conflicts:
        print("Change is NOT a solution")
        applyChangeToDB(table, prev)
        return False, new_conflicts
    else:
        print("Change IS a solution")
        return True, new_conflicts

ret = getDifferencesFromDatabases(projectNumber)


# Copiar a base de dados inicial, se não existir
# if not os.path.exists('./database/Project' + str(projectNumber) + '/duplicate_initial_database.db'):
src = './database/Project' + str(projectNumber) + '/initial_database.db'
dst = './database/Project' + str(projectNumber) + '/duplicate_initial_database.db'
shutil.copy2(src, dst)

duplicateInitialDB = sqlite3.connect(dst, check_same_thread=False)
duplicateInitialDB.row_factory = sqlite3.Row


queue = []
for change in changesDict:
    if change == 0:
        continue
    table, prev, new = changesDict[change]
    queue.append((change, table, prev, new))

# create a directed graph
G = nx.DiGraph()

conflicts = []
while len(queue) > 0:
    change, table, prev, new = queue.pop(0)
    print(change, table, prev, new)
    
    G.add_node(change, table=table, prev=prev, new=new)

    # Aplicar a alteração desse nó à BD
    new_conflicts = applyChangeToDB(table, new)

    # Verificar se isso gera um conflito
    if len(new_conflicts) > 0:
        # Procurar nó que resolve o conflito
        generated_conflicts = list(set(new_conflicts))
        node_source = change
        print("Generated conflicts: ", generated_conflicts)
        while len(generated_conflicts) > 0:
            generated_conflict = generated_conflicts.pop(0)
            print("Fixing the generated conflict: ", generated_conflict)
            conflict_solved = False

            while not conflict_solved:
                node = queue.pop(0)
                change, table, prev, new = node

                # Aplicar essa alteração à base de dados e verificar se resolve o conflito
                isSolution, new_conflicts = checkChangeToDB(generated_conflict, table, prev, new)
                input("Press Enter to continue...")

                if isSolution:
                    conflict_solved = True

                    # Criar aresta entre os nós (direcionada, na direção do que resolve o conflito)
                    print("Adding edge between ", node_source, change)
                    G.add_edge(node_source, change)

                    # new_generated_conflicts = list(set(new_conflicts) - set(conflicts))

                else:
                    queue.append(node)
                    print("Adding node back to queue: ", node)
        conflicts = new_conflicts

    input("Press Enter to continue...")
        
        
# drawing the directed conflict graph
pos = nx.spring_layout(G)
nx.draw(G, pos, with_labels=True, node_size=3000, node_color="skyblue", node_shape="s", alpha=0.5, linewidths=4)
plt.title("Graph")
plt.show()

