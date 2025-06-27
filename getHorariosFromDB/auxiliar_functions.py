from FeupScheduleEditor.models import AulaChange, AulaInfo
import sqlite3
from pathlib import Path

def converter_horario(num):
    hora, minuto = divmod(num, 100)
    return f"{hora:02d}:{minuto:02d}"   

def calculate_hora_final(horaInicial, duracao):
    horaInicial = horaInicial.replace(":", "")
    hours = int(horaInicial[:2])
    minutes = int(horaInicial[2:])
    total_minutes = hours * 60 + minutes + duracao * 30
    final_hours = total_minutes // 60
    final_minutes = total_minutes % 60
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

            if hora_inicio < aula_end_min and hora_fim > aula_hora_min:
                conflicts.append(aula_id)
                print(f"[DEBUG] Sala conflict: Aula {aula_id} (UC {uc_nome})")

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

            if hora_inicio < aula_end_min and hora_fim > aula_hora_min:
                conflicts.append(aula_id)
                print(f"[DEBUG] Docente conflict: Aula {aula_id} (UC {uc_nome})")
                print(f"Checking docente {docente} on aula -> {exclude_aula_id}, {dia_semana} at {hora_inicio//60}-{hora_fim//60} vs aula {aula_id} at {dia_semana} {aula_hora_str}-{aula_end_min//60}:{aula_end_min%60}")


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

            if hora_inicio < aula_end_min and hora_fim > aula_hora_min and aula_id not in conflicts:
                conflicts.append(aula_id)
                print(f"[DEBUG] Turma conflict: Aula {aula_id} (UC {uc_nome})")

    return conflicts

def check_aula_change_conflicts(change: AulaChange, project_number, mode):
    conflicts = []
    db_path = Path(f'./database/Project{project_number}/{mode}_database.db')

    try:
        connection = sqlite3.connect(str(db_path))
        cursor = connection.cursor()

        new_aula = change.new
        if not new_aula:
            return conflicts
        if new_aula.id == 3426:
            print(f"IM HERE: {new_aula.dia}")

        dia_semana = new_aula.dia
        hora_inicio = time_str_to_minutes(new_aula.hora_inicio)
        hora_fim = time_str_to_minutes(new_aula.hora_fim)
        aula_id = change.previous.id if change.previous else None

        #print(f"[DEBUG] Checking conflicts for new class ({aula_id}): Day {dia_semana}, Start time {hora_inicio}, End time {hora_fim}")
        
        conflicts.extend(
            check_sala_conflicts(cursor, new_aula.salas_ids, dia_semana, hora_inicio, hora_fim, aula_id)
        )

        conflicts.extend(
            check_docente_conflicts(cursor, new_aula.docentes_ids, dia_semana, hora_inicio, hora_fim, aula_id)
        )

        conflicts.extend(
            check_turma_conflicts(cursor, new_aula.turmas_ids, dia_semana, hora_inicio, hora_fim, aula_id)
        )

        # Check for red block conflicts
        #red_conflicts = check_bloco_vermelho_conflicts(cursor, new_aula, dia_semana, hora_inicio, hora_fim)
        #if red_conflicts:
        #    conflicts.extend(red_conflicts)

    except sqlite3.Error as e:
        print(f"Database error: {e}")
        conflicts.append("database_error")
    except Exception as e:
        print(f"Unexpected error: {e}")
        conflicts.append(f"unexpected_error:{str(e)}")
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'connection' in locals():
            connection.close()
    
    return conflicts

def check_bloco_vermelho_conflicts(cursor, new_aula, dia_semana, hora_inicio, hora_fim):
    """
    Checks if the given aula conflicts with any blocosVermelhos.
    Returns list of conflicting aula IDs or "red" for red block conflicts.
    """
    conflicts = []

    def bloco_time_overlaps(bloco_hora):
        bloco_hora_str = converter_horario(bloco_hora)
        bloco_hora_min = time_str_to_minutes(bloco_hora_str)
        bloco_end_min = bloco_hora_min + 30  # blocosVermelhos are always 30min
        return hora_inicio < bloco_end_min and hora_fim > bloco_hora_min

    # Check for turma red blocks
    for turma in getattr(new_aula, "turmas_ids", []):
        cursor.execute("""
            SELECT a.id, a.horaInicial, a.duracao, uc.nome
            FROM aula a
            JOIN aulaTurmas at ON a.id = at.idAula
            JOIN aulaUC auc ON a.id = auc.idAula
            JOIN uc ON auc.idUC = uc.codigo
            JOIN blocoTurma bt ON at.idTurma = bt.idTurma
            JOIN blocosVermelhos bv ON bt.idBloco = bv.id
            WHERE bt.idTurma = ? 
            AND bv.diaSemana = ?
            AND a.id != ?
        """, (turma, dia_semana, getattr(new_aula, "id", -1)))
        
        for aula_id, aula_hora, aula_duracao, uc_nome in cursor.fetchall():
            conflicts.append(aula_id)
            print(f"[DEBUG] Red block conflict (turma): Aula {aula_id} (UC {uc_nome})")

    # Similar queries for docentes, ucs, and salas would go here
    # For simplicity, I'm showing the pattern with turmas
    
    return conflicts

def generate_node_id():
    if not hasattr(generate_node_id, "counter"):
        generate_node_id.counter = 0
    node_id = generate_node_id.counter
    generate_node_id.counter += 1
    return node_id