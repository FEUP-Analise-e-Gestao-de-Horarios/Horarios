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
import time


projectNumber = 23
changeOrder = 1

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
changesDict = dict()

def addChangeToDict(table_name, primaryKey, diff_data1, diff_data2):
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
        #print("conflicts: ", conflicts, "\n")

    elif table == "aula":
        changeAula(projectNumber, new)
        diaAula = new["diaSemana"]
        horaAula = new["horaInicial"]
        aulaId = new["id"]
        # print("diaAula: ", diaAula, " horaAula: ", horaAula, " aulaId: ", aulaId)
        conflicts = findAnyConflicts(projectNumber, diaAula, horaAula, aulaId)
        #print("conflicts: ", conflicts, "\n")

    elif table == "aulaSala":
        changeAulaSala(projectNumber, new["idAula"], new["idSala"])
        diaAula, horaAula = getAulaDiaHora(new["idAula"])
        aulaId = new["idAula"]
        # print("diaAula: ", diaAula, " horaAula: ", horaAula, " aulaId: ", aulaId)
        conflicts = findAnyConflicts(projectNumber, diaAula, horaAula, aulaId)
        #print("conflicts: ", conflicts, "\n")

    elif table == "aulaDocente":
        changeAulaDocente(projectNumber, new["idAula"], new["idDocente"])
        diaAula, horaAula = getAulaDiaHora(new["idAula"])
        aulaId = new["idAula"]
        # print("diaAula: ", diaAula, " horaAula: ", horaAula, " aulaId: ", aulaId)
        conflicts = findAnyConflicts(projectNumber, diaAula, horaAula, aulaId)
        #print("conflicts: ", conflicts, "\n")

    return conflicts

def generateConflicts(table, prev, new):
    print(f'{table} {prev} {new}')
    conflicts = applyChangeToDB(table, new)
    applyChangeToDB(table, prev)
    print("Conflicts next: ", conflicts)
    
    if len(conflicts) > 0:
        return True
    else:
        return False


def checkChangeToDB(generated_conflict, table, prev, new):
    print("Applying change to DB: ", new)
    new_conflicts = applyChangeToDB(table, new)

    if generated_conflict in new_conflicts:
        print("Change is NOT a solution\n")
        new_conflicts = applyChangeToDB(table, prev)
        print("New Conlficts", new_conflicts)
        return False, new_conflicts
    else:
        print("Change IS a solution\n")
        print("New Conlficts", new_conflicts)
        return True, new_conflicts

def findBestChange(conflict, visited):
    print("Finding change for conflict: ", conflict)
    for change in changesDict:
        if change in visited:
            continue
        table, prev, new = changesDict[change]
        print("Checking if change", change, "is a solution...")
        solve_conflict, new_conflicts = checkChangeToDB(conflict, table, prev, new)
        if solve_conflict:
            return change, new_conflicts
    print("ERROR: No solution found for conflict: ", conflict)
    return None, None

def dfs_visit(graph, change, visited):
    global changeOrder
    print("\n")
    print("Visiting change", change)
    print("Visited changes", visited)
    if change not in visited:
        table, prev, new = changesDict[change]
        visited.add(change)
        conflicts = applyChangeToDB(table, new)
        graph.add_node(change, table=table, prev=prev, new=new, order=changeOrder)
        changeOrder += 1
        print("Conflicts: ", conflicts)
        while len(conflicts) > 0:
            conflict = conflicts.pop(0)
            # find the next change that solves the conflict
            next_change, new_conflicts = findBestChange(conflict, visited)
            if next_change is None:
                continue # No solution found for this conflict
            table, prev, new = changesDict[next_change]
            graph.add_node(next_change, table=table, prev=prev, new=new, order=changeOrder)
            graph.add_edge(change, next_change)
            # print("New Conflicts: ", new_conflicts)
            # input("Press Enter to continue...")
            conflicts = dfs_visit(graph, next_change, visited)
            # print("Conflicts: ", conflicts)
        return conflicts

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
    table, prev, new = changesDict[change]
    queue.append((change, table, prev, new))

# create a directed graph
G = nx.DiGraph()

visited = set()

changeNum = 1
while changeNum <= len(changesDict):
    table, prev, new = changesDict[changeNum]
    print("\nChange", changeNum)
    if changeNum not in visited and not generateConflicts(table, prev, new):
        applyChangeToDB(table, new)
        visited.add(changeNum)
        G.add_node(changeNum, table=table, prev=prev, new=new, order=changeOrder)
        changeOrder += 1
        changeNum = 1
        continue
    changeNum += 1


for change, table, prev, new in queue:
    # print(change, table, prev, new)
    print("For Loop", change)
    if change not in visited:
        dfs_visit(G, change, visited)

    # input("Press Enter to continue...")
        

print("\n\n")
print("changesDict")
changesDescription = str()
for change in changesDict:
    if change == 0:
        continue
    table, prev, new = changesDict[change]
    changesDescription += f"{change} {table} \n    Prev: {prev} \n    New: {new}\n"
    print(change, table, prev, new)
print("\n\n")

# plt.text(-2.5, -1, changesDescription, fontsize=10, bbox=None)

pos = nx.spring_layout(G, k=1.5)

for key, value in pos.items():
    pos[key] = (value[0] + 1, value[1])

labels = {node: f'{node}\nOrd:{G.nodes[node]["order"]}' for node in G.nodes()}

nx.draw(G, pos, labels=labels, with_labels=True, arrows=True, node_size=3000, font_size=20, node_shape="s")

plt.xlim(-2, 2)
plt.ylim(-2, 2)

plt.show()
