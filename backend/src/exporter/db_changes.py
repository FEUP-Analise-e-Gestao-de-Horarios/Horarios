import sqlite3

from src.getHorariosFromDB.conflictFunctionsDup import findAnyConflicts


def change_aula_turma(project_number, id_aula, id_turma):
    path = f"Project{project_number}"
    conn = sqlite3.connect(
        f"./database/{path}/duplicate_initial_database.db",
        check_same_thread=False,
    )
    cursor = conn.cursor()
    cursor.execute("""UPDATE aulaTurmas SET idTurma=? WHERE idAula=?""", (id_turma, id_aula))
    conn.commit()


def change_aula(project_number, aula):
    path = f"Project{project_number}"
    conn = sqlite3.connect(
        f"./database/{path}/duplicate_initial_database.db",
        check_same_thread=False,
    )
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE aula SET horaInicial=?, duracao=?, diaSemana=?, teorico=?, semanaInicial=?, semanaFinal=? WHERE id=?""",
        (
            aula["horaInicial"],
            aula["duracao"],
            aula["diaSemana"],
            aula["teorico"],
            aula["semanaInicial"],
            aula["semanaFinal"],
            aula["id"],
        ),
    )
    conn.commit()


def change_aula_sala(project_number, id_aula, id_sala):
    path = f"Project{project_number}"
    conn = sqlite3.connect(
        f"./database/{path}/duplicate_initial_database.db",
        check_same_thread=False,
    )
    cursor = conn.cursor()
    cursor.execute("""UPDATE aulaSala SET idSala=? WHERE idAula=?""", (id_sala, id_aula))
    conn.commit()


def change_aula_docente(project_number, id_aula, id_docente):
    path = f"Project{project_number}"
    conn = sqlite3.connect(
        f"./database/{path}/duplicate_initial_database.db",
        check_same_thread=False,
    )
    cursor = conn.cursor()
    cursor.execute(
        """UPDATE aulaDocente SET idDocente=? WHERE idAula=?""",
        (id_docente, id_aula),
    )
    conn.commit()


def get_aula_dia_hora(project_number, aula_id):
    path = f"Project{project_number}"
    conn = sqlite3.connect(
        f"./database/{path}/duplicate_initial_database.db",
        check_same_thread=False,
    )
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM aula WHERE id=?", (aula_id,))
    aula_row = cursor.fetchone()
    return aula_row["diaSemana"], aula_row["horaInicial"]


def apply_change_to_db(project_number, table, new):
    conflicts = []

    if table == "aulaTurmas":
        change_aula_turma(project_number, new["idAula"], new["idTurma"])
        dia_aula, hora_aula = get_aula_dia_hora(project_number, new["idAula"])
        conflicts = findAnyConflicts(project_number, dia_aula, hora_aula, new["idAula"])

    elif table == "aula":
        change_aula(project_number, new)
        conflicts = findAnyConflicts(
            project_number,
            new["diaSemana"],
            new["horaInicial"],
            new["id"],
        )

    elif table == "aulaSala":
        change_aula_sala(project_number, new["idAula"], new["idSala"])
        dia_aula, hora_aula = get_aula_dia_hora(project_number, new["idAula"])
        conflicts = findAnyConflicts(project_number, dia_aula, hora_aula, new["idAula"])

    elif table == "aulaDocente":
        change_aula_docente(project_number, new["idAula"], new["idDocente"])
        dia_aula, hora_aula = get_aula_dia_hora(project_number, new["idAula"])
        conflicts = findAnyConflicts(project_number, dia_aula, hora_aula, new["idAula"])

    return conflicts


def generate_conflicts(project_number, table, prev, new):
    print(f"{table} {prev} {new}")
    conflicts = apply_change_to_db(project_number, table, new)
    apply_change_to_db(project_number, table, prev)
    print("Conflicts next: ", conflicts)
    return len(conflicts) > 0


def check_change_to_db(project_number, generated_conflict, table, prev, new):
    print("Applying change to DB: ", new)
    new_conflicts = apply_change_to_db(project_number, table, new)

    if generated_conflict in new_conflicts:
        print("Change is NOT a solution\n")
        new_conflicts = apply_change_to_db(project_number, table, prev)
        print("New Conlficts", new_conflicts)
        return False, new_conflicts

    print("Change IS a solution\n")
    print("New Conlficts", new_conflicts)
    return True, new_conflicts
