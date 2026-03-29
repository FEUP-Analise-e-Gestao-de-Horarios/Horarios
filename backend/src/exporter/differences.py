import sqlite3

from src.getHorariosFromDB.comparingDatabases import (
    handleAulaDocente,
    handleAulas,
    handleAulaSala,
    handleAulaTurmas,
    handleAulaUC,
    handleDocentes,
    handleSalas,
    sortChanges,
)


def add_change_to_dict(changes_dict, table_name, primary_key, diff_data1, diff_data2):
    new_changes = [dict(row) for row in diff_data1]
    prev_changes = [dict(row) for row in diff_data2]

    for prev in prev_changes:
        for new in new_changes:
            if prev[primary_key] == new[primary_key]:
                changes_dict[len(changes_dict) + 1] = (table_name, prev, new)
                break


def get_primary_key(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = cursor.fetchall()
    for column in columns:
        if column[5]:
            return column[1]
    return None


def get_differences_from_databases(project_number, changes_dict):
    handlers = {
        "aulaSala": handleAulaSala,
        "docentes": handleDocentes,
        "salas": handleSalas,
        "aulaDocente": handleAulaDocente,
        "aula": handleAulas,
        "aulaTurmas": handleAulaTurmas,
        "aulaUC": handleAulaUC,
    }

    path = f"Project{project_number}"
    conn_db = sqlite3.connect(f"./database/{path}/general_database.db", check_same_thread=False)
    conn_db.row_factory = sqlite3.Row
    cursor_db = conn_db.cursor()

    conn_ini = sqlite3.connect(f"./database/{path}/initial_database.db", check_same_thread=False)
    conn_ini.row_factory = sqlite3.Row
    cursor_ini = conn_ini.cursor()

    cursor_db.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables1 = cursor_db.fetchall()

    cursor_ini.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables2 = cursor_ini.fetchall()

    every_change = []

    for table1 in tables1:
        table1_name = table1[0]

        for table2 in tables2:
            table2_name = table2[0]

            if table1_name != table2_name:
                continue

            cursor_db.execute(f"SELECT * FROM {table1_name};")
            data1 = cursor_db.fetchall()

            cursor_ini.execute(f"SELECT * FROM {table2_name};")
            data2 = cursor_ini.fetchall()

            set1 = set(data1)
            set2 = set(data2)

            if set1 != set2:
                diff_data1 = set1 - set2
                diff_data2 = set2 - set1

                primary_key = get_primary_key(conn_db, table1_name)
                add_change_to_dict(changes_dict, table1_name, primary_key, diff_data1, diff_data2)
                every_change.append(handlers[table1_name](set1, set2, project_number))

            break

    formatted_changes = [item for sublist in every_change for item in sublist]
    sorted_changes = sorted(formatted_changes, key=sortChanges)
    return [string for precedence, string, id in sorted_changes]
