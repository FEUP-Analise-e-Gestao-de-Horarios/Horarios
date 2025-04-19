from FeupScheduleEditor.models import AulaChange, AulaInfo
import sqlite3


def generate_node_id():
    """Generates a unique numeric node id on each call."""
    if not hasattr(generate_node_id, "counter"):
        generate_node_id.counter = 0  # Initialize the counter
    node_id = generate_node_id.counter
    generate_node_id.counter += 1
    return node_id

def check_aula_change_conflicts(aula_change: AulaChange, project_number: int) -> list[tuple[str, int]]:
    """
    Check if the proposed aula change has any scheduling conflicts in the database.
    Returns list of (uc_id, aula_id) pairs that conflict with the proposed change.
    
    Args:
        aula_change: The AulaChange object containing previous and new aula info
        project_number: The project number to identify the database
    
    Returns:
        list: List of (uc_id, aula_id) tuples representing conflicts
              Empty list if no conflicts found
    """
    if aula_change.new is None:
        return {}  # No conflicts if removing an aula
    
    path = f"Project{project_number}"
    db_path = f'./database/{path}/general_database.db'
    conflicts = {}
    
    try:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Extract time information from the new aula
        dia = aula_change.new.dia
        hora_inicio = aula_change.new.hora_inicio
        hora_fim = aula_change.new.hora_fim
        aula_id = aula_change.new.id
        
        # Convert times to minutes for comparison
        start_min = int(hora_inicio) * 60
        end_min = int(hora_fim) * 60
        
        # Check all potential conflicts (docentes, turmas, salas) in one query
        cursor.execute("""
            SELECT DISTINCT auc.idUC, a.id
            FROM aula a
            JOIN aulaUC auc ON a.id = auc.idAula
            WHERE a.dia = ?
            AND a.id != ?
            AND (
                -- Conflicts with docentes
                EXISTS (
                    SELECT 1 FROM aulaDocente ad 
                    WHERE ad.idAula = a.id 
                    AND ad.idDocente IN (%s)
                )
                OR
                -- Conflicts with turmas
                EXISTS (
                    SELECT 1 FROM aulaTurmas at 
                    WHERE at.idAula = a.id 
                    AND at.idTurma IN (%s)
                )
                OR
                -- Conflicts with salas
                EXISTS (
                    SELECT 1 FROM aulaSala asala 
                    WHERE asala.idAula = a.id 
                    AND asala.idSala IN (%s)
                )
            )
            AND (
                -- Time overlap conditions
                (? >= a.hora_inicio AND ? < a.hora_inicio + a.duracao)
                OR
                (a.hora_inicio >= ? AND a.hora_inicio < ?)
            )
        """ % (
            ','.join(['?']*len(aula_change.new.docentes_ids)),
            ','.join(['?']*len(aula_change.new.turmas_ids)),
            ','.join(['?']*len(aula_change.new.salas_ids))
        ),
            dia, aula_id,
            *aula_change.new.docentes_ids,
            *aula_change.new.turmas_ids,
            *aula_change.new.salas_ids,
            start_min, start_min,
            start_min, end_min
        )
        
        #conflicts = [(row['idUC'], row['id']) for row in cursor.fetchall()]
        for row in cursor.fetchall():
            conflicts[row['id']].append(row['idUC'])
        # Also check for blocosVermelhos conflicts
        #
        #cursor.execute("""
        #    SELECT DISTINCT buc.idUC, CONCAT('block_', bv.id)
        #    FROM blocosVermelhos bv
        #    LEFT JOIN blocoUC buc ON bv.id = buc.idBloco
        #    WHERE bv.diaSemana = ?
        #    AND (
        #        -- Conflicts with docentes
        #        EXISTS (
        #            SELECT 1 FROM blocoDocente bd 
        #            WHERE bd.idBloco = bv.id 
        #            AND bd.idDocente IN (%s)
        #        )
        #        OR
        #        -- Conflicts with turmas
        #        EXISTS (
        #            SELECT 1 FROM blocoTurma bt 
        #            WHERE bt.idBloco = bv.id 
        #            AND bt.idTurma IN (%s)
        #        )
        #        OR
        #        -- Conflicts with salas
        #        EXISTS (
        #            SELECT 1 FROM salaBloco sb 
        #            WHERE sb.idBloco = bv.id 
        #            AND sb.idSala IN (%s)
        #        )
        #    )
        #    AND (
        #        -- Time overlap conditions
        #        (? >= TIME_TO_MINUTES(bv.hora) AND ? < TIME_TO_MINUTES(bv.hora) + ?)
        #        OR
        #        (TIME_TO_MINUTES(bv.hora) >= ? AND TIME_TO_MINUTES(bv.hora) < ?)
        #    )
        #""" % (
        #    ','.join(['?']*len(aula_change.new.docentes_ids)),
        #    ','.join(['?']*len(aula_change.new.turmas_ids)),
        #    ','.join(['?']*len(aula_change.new.salas_ids))
        #),
        #    dia,
        #    *aula_change.new.docentes_ids,
        #    *aula_change.new.turmas_ids,
        #    *aula_change.new.salas_ids,
        #    start_min, start_min, (end_min - start_min),
        #    start_min, end_min
        #)
        #
        #conflicts.extend([(row[0], int(row[1].replace('block_', ''))) 
        #             for row in cursor.fetchall() if row[0] is not None])
        #
        return conflicts
    
    except sqlite3.Error as e:
        print(f"Database error: {e}")
        return []  # Return empty list on error
    finally:
        if conn:
            conn.close()

