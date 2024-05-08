from comparingDatabases import handleAulaSala
from comparingDatabases import handleDocentes
from comparingDatabases import handleSalas
from comparingDatabases import handleAulaDocente
from comparingDatabases import handleAulas
from comparingDatabases import handleAulaTurmas
from comparingDatabases import handleAulaUC
from comparingDatabases import sortChanges
import sqlite3
import networkx as nx
import matplotlib.pyplot as plt
from itertools import groupby
import shutil

projectNumber = 5

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
    print("Table: ", table_name)
    print("Primary Key: ", primaryKey)

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


ret = getDifferencesFromDatabases(projectNumber)

# G = nx.DiGraph()
# nodes1_100 = ["node "+str(i) for i in range(1, 101)]

# G.add_node("Root")
# G.add_nodes_from(nodes1_100)

# nx.draw(G, with_labels=True)
# plt.show()


# Copiar a base de dados inicial
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

# Algoritmo de construcao do grafo
while len(queue) > 0:
    change, table, prev, new = queue.pop(0)
    print(change, table, prev, new)

    # Aplicar a alteração desse nó à BD
    # mf.switchAulas(projectNumber, prev['idAula'], new['idAula'])



    # Verificar se isso gera um conflito
    # Procurar nó que resolve o conflito
    # Aplicar essa alteração à base de dados
    # Criar aresta entre os nós (direcionada, na direção do que resolve o conflito)
