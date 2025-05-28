from FeupScheduleEditor.models import AulaChange, AulaInfo
import sqlite3
from pathlib import Path

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

def time_str_to_minutes(time_str):
    """Convert 'HH:MM' string to total minutes."""
    hours, minutes = map(int, time_str.split(":"))
    total_minutes = hours * 60 + minutes
    return total_minutes

def calculate_duracao(horaInicio_str, horaFim_str):
    """Calculate the duration in 30-minute blocks from HH:MM strings."""
    h_start, m_start = map(int, horaInicio_str.split(":"))
    h_end, m_end = map(int, horaFim_str.split(":"))
    total_start = h_start * 60 + m_start
    total_end = h_end * 60 + m_end
    duration = (total_end - total_start) // 30
    return duration

def check_sala_conflicts(cursor, salas_ids, dia_semana, hora_inicio, hora_fim, exclude_aula_id=None):
    conflicts = []
    for sala in salas_ids:
        cursor.execute("""
            SELECT a.id, a.horaInicial, a.duracao, uc.nome
            FROM aula a
            JOIN aulaSala asl ON a.id = asl.idAula
            JOIN aulaUC auc ON a.id = auc.idAula
            JOIN uc ON auc.idUC = uc.codigo
            WHERE asl.idSala = ? 
            AND a.diaSemana = ? 
            AND a.id != ?
        """, (sala, dia_semana, exclude_aula_id or -1))
        
        for aula_id, aula_hora, aula_duracao, uc_nome in cursor.fetchall():
            aula_hora_str = converter_horario(aula_hora)
            aula_hora_min = time_str_to_minutes(aula_hora_str)
            aula_end_min = aula_hora_min + int(aula_duracao) * 30

            print(f"[DEBUG] Checking room conflicts: Aula {aula_id} from {aula_hora_min} (ends at {aula_end_min} minutes) against input time from {hora_inicio} to {hora_fim}")  # Debug print

            if hora_inicio < aula_end_min and hora_fim > aula_hora_min:
                # Only append the aula_id to the conflicts list
                conflicts.append(aula_id)
                
                # Print detailed debug information
                print(f"[DEBUG] Conflict found for Sala {sala}: Aula {aula_id} (UC {uc_nome}) from {aula_hora_str} to {aula_end_min} (duration {aula_duracao} blocks)")  # Debug print

    return conflicts

def check_docente_conflicts(cursor, docentes_ids, dia_semana, hora_inicio, hora_fim, exclude_aula_id=None):
    conflicts = []
    for docente in docentes_ids:
        cursor.execute("""
            SELECT a.id, a.horaInicial, a.duracao, uc.nome, d.nome
            FROM aula a
            JOIN aulaDocente ad ON a.id = ad.idAula
            JOIN docentes d ON ad.idDocente = d.numeroMecanografico
            JOIN aulaUC auc ON a.id = auc.idAula
            JOIN uc ON auc.idUC = uc.codigo
            WHERE d.numeroMecanografico = ?
            AND a.diaSemana = ?
            AND a.id != ?
        """, (docente, dia_semana, exclude_aula_id or -1))
        
        for aula_id, aula_hora, aula_duracao, uc_nome, docente_nome in cursor.fetchall():
            aula_hora_str = converter_horario(aula_hora)
            aula_hora_min = time_str_to_minutes(aula_hora_str)
            aula_end_min = aula_hora_min + int(aula_duracao) * 30

            print(f"[DEBUG] Checking docente conflicts: Aula {aula_id} from {aula_hora_str} (ends at {aula_end_min} minutes) against input time from {hora_inicio} to {hora_fim}")  # Debug print

            if hora_inicio < aula_end_min and hora_fim > aula_hora_min:
                # Only append the aula_id to the conflicts list
                conflicts.append(aula_id)
                
                # Print detailed debug information
                print(f"[DEBUG] Conflict found for Docente {docente_nome} ({docente}): Aula {aula_id} (UC {uc_nome}) from {aula_hora_str} to {aula_end_min} (duration {aula_duracao} blocks)")  # Debug print
    return conflicts

def check_turma_conflicts(cursor, turmas_ids, dia_semana, hora_inicio, hora_fim, exclude_aula_id=None):
    conflicts = []
    for turma in turmas_ids:
        cursor.execute("""
            SELECT a.id, a.horaInicial, a.duracao, uc.nome, t.codigo
            FROM aula a
            JOIN aulaTurmas at ON a.id = at.idAula
            JOIN turmas t ON at.idTurma = t.codigo
            JOIN aulaUC auc ON a.id = auc.idAula
            JOIN uc ON auc.idUC = uc.codigo
            WHERE t.codigo = ?
            AND a.diaSemana = ?
            AND a.id != ?
        """, (turma, dia_semana, exclude_aula_id or -1))
        
        for aula_id, aula_hora, aula_duracao, uc_nome, turma_cod in cursor.fetchall():
            aula_hora_str = converter_horario(aula_hora)
            aula_hora_min = time_str_to_minutes(aula_hora_str)
            aula_end_min = aula_hora_min + int(aula_duracao) * 30

            print(f"[DEBUG] Checking turma conflicts: Aula {aula_id} from {aula_hora_min} (ends at {aula_end_min} minutes) against input time from {hora_inicio} to {hora_fim}")  # Debug print

            if hora_inicio < aula_end_min and hora_fim > aula_hora_min:
                # Only append the aula_id to the conflicts list
                conflicts.append(aula_id)
                
                # Print detailed debug information
                print(f"[DEBUG] Conflict found for Turma {turma_cod}: Aula {aula_id} (UC {uc_nome}) from {aula_hora_str} to {aula_end_min} (duration {aula_duracao} blocks)")  # Debug print
    return conflicts

def check_aula_change_conflicts(change: AulaChange, project_number):
    conflicts = []
    db_path = Path(f'./database/Project{project_number}/general_database.db')

    try:
        connection = sqlite3.connect(str(db_path))
        cursor = connection.cursor()

        new_aula = change.new
        if not new_aula:
            return conflicts

        dia_semana = new_aula.dia
        hora_inicio = time_str_to_minutes(new_aula.hora_inicio)
        hora_fim = time_str_to_minutes(new_aula.hora_fim)
        aula_id = change.previous.id if change.previous else None

        print(f"[DEBUG] Checking conflicts for new class ({aula_id}): Day {dia_semana}, Start time {hora_inicio}, End time {hora_fim}")  # Debug print
        
        if change.check_salas():
            print(f"[DEBUG] CHECKING SALAS")  # Debug print
            conflicts.extend(
                check_sala_conflicts(cursor, new_aula.salas_ids, dia_semana, hora_inicio, hora_fim, aula_id)
            )

        if change.check_docentes():
            print(f"[DEBUG] CHECKING DOCENTES")  # Debug print
            conflicts.extend(
                check_docente_conflicts(cursor, new_aula.docentes_ids, dia_semana, hora_inicio, hora_fim, aula_id)
            )

        if  change.check_turmas():
            print(f"[DEBUG] CHECKING TURMAS")  # Debug print
            conflicts.extend(
                check_turma_conflicts(cursor, new_aula.turmas_ids, dia_semana, hora_inicio, hora_fim, aula_id)
            )

        # ---- MOVE THIS INSIDE THE TRY, BEFORE FINALLY ----
        if check_bloco_vermelho_conflicts(cursor, new_aula, dia_semana, hora_inicio, hora_fim):
            conflicts.append("red")

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conflicts.append("Erro ao verificar conflitos na base de dados")
    except Exception as e:
        print(f"Unexpected error: {e}")
        conflicts.append(f"Erro inesperado: {str(e)}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()
    return conflicts

def generate_node_id():
    if not hasattr(generate_node_id, "counter"):
        generate_node_id.counter = 0
    node_id = generate_node_id.counter
    generate_node_id.counter += 1
    return node_id

def check_bloco_vermelho_conflicts(cursor, new_aula, dia_semana, hora_inicio, hora_fim):
    """
    Checks if the given aula (by AulaInfo) has a conflict with any blocosVermelhos,
    using blocoTurma, blocoDocente, blocoUC, salaBloco association tables.
    Returns a list of conflicting bloco ids (with type for debug).
    """
    conflicts = []

    # Helper to check time overlap
    def bloco_time_overlaps(bloco_hora):
        bloco_hora_str = converter_horario(bloco_hora)
        bloco_hora_min = time_str_to_minutes(bloco_hora_str)
        bloco_end_min = bloco_hora_min + 30  # blocosVermelhos are always 30min blocks
        return hora_inicio < bloco_end_min and hora_fim > bloco_hora_min

    # Turmas
    for turma in getattr(new_aula, "turmas_ids", []):
        cursor.execute("""
            SELECT bv.id, bv.hora
            FROM blocoTurma bt
            JOIN blocosVermelhos bv ON bt.idBloco = bv.id
            WHERE bt.idTurma = ? AND bv.diaSemana = ?
        """, (turma, dia_semana))
        for bloco_id, bloco_hora in cursor.fetchall():
            if bloco_time_overlaps(bloco_hora):
                print(f"[DEBUG] Conflict with blocoVermelho (turma) {bloco_id} at {bloco_hora}")  # Debug print
                conflicts.append({"type": "turma", "bloco_id": bloco_id})

    # Docentes
    for docente in getattr(new_aula, "docentes_ids", []):
        cursor.execute("""
            SELECT bv.id, bv.hora
            FROM blocoDocente bd
            JOIN blocosVermelhos bv ON bd.idBloco = bv.id
            WHERE bd.idDocente = ? AND bv.diaSemana = ?
        """, (docente, dia_semana))
        for bloco_id, bloco_hora in cursor.fetchall():
            if bloco_time_overlaps(bloco_hora):
                print(f"[DEBUG] Conflict with blocoVermelho (docente) {bloco_id} at {bloco_hora}")  # Debug print
                conflicts.append({"type": "docente", "bloco_id": bloco_id})

    # UCs
    for uc in getattr(new_aula, "ucs_ids", []):
        cursor.execute("""
            SELECT bv.id, bv.hora
            FROM blocoUC bu
            JOIN blocosVermelhos bv ON bu.idBloco = bv.id
            WHERE bu.idUC = ? AND bv.diaSemana = ?
        """, (uc, dia_semana))
        for bloco_id, bloco_hora in cursor.fetchall():
            if bloco_time_overlaps(bloco_hora):
                print(f"[DEBUG] Conflict with blocoVermelho (uc) {bloco_id} at {bloco_hora}")  # Debug print
                conflicts.append({"type": "uc", "bloco_id": bloco_id})

    # Salas
    for sala in getattr(new_aula, "salas_ids", []):
        cursor.execute("""
            SELECT bv.id, bv.hora
            FROM salaBloco sb
            JOIN blocosVermelhos bv ON sb.idBloco = bv.id
            WHERE sb.idSala = ? AND bv.diaSemana = ?
        """, (sala, dia_semana))
        for bloco_id, bloco_hora in cursor.fetchall():
            if bloco_time_overlaps(bloco_hora):
                print(f"[DEBUG] Conflict with blocoVermelho (sala) {bloco_id} at {bloco_hora}")  # Debug print
                conflicts.append({"type": "sala", "bloco_id": bloco_id})

    return conflicts