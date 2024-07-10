import sqlite3
from re import sub

def organizeBlocos(blocos, dia_semana):
    final_blocos = []
    for i in blocos:
        #print(f"Hora: {i['hora']} / Dia: {i['diaSemana']}")
        if (i['diaSemana']==dia_semana):
            final_blocos.append((i['hora'], i['diaSemana']))
    return final_blocos

def getAbreviacaoFromMecanografico(ProjectNumber, numMecanografico):
    # Establish a connection to the database
    path = "Project" + str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    query = """
    SELECT abreviacao FROM docentes WHERE numeroMecanografico=?
    """
    cursor.execute(query, (numMecanografico,))
    result = cursor.fetchone()[0]
    return result

def getInformationFromAula(ProjectNumber, idAula, db="general_database.db"):
    # Establish a connection to the database
    path = "Project" + str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/'+db, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    query = """
    SELECT a.horaInicial as hora, a.diaSemana as dia, SUBSTR(u.sigla, 1, INSTR(u.sigla, '(')-1) AS uc_sigla, at.idTurma as turma, u.codigo as uc_code
    FROM aula AS a
    JOIN aulaTurmas AS at ON a.id = at.idAula
    JOIN aulaUC AS au ON a.id = au.idAula
    JOIN uc AS u ON au.idUC = u.codigo
    WHERE a.id = ? AND at.idAula = ? AND au.idAula = ?;
    """
    cursor.execute(query, (idAula, idAula, idAula))
    result = cursor.fetchone()
    return result

def getAulaFromSalaAndTime(ProjectNumber, hora_inicial, dia_semana, sala, idAulaToCheck):
    if (sala=="Online"):
        return []
    # Establish a connection to the database
    path = "Project" + str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    result = []
    for a in getSalaHorario(ProjectNumber, sala):
        if (a["diaSemana"] == dia_semana):
            query = """SELECT duracao, horaInicial FROM aula WHERE id=?"""
            cursor.execute(query, (a[0],))
            resultado = cursor.fetchone()
            duracao = resultado[0]
            horaInicio = resultado[1]
            hora = horaInicio
            while duracao > 1:
                if (int(hora) == int(hora_inicial)):
                    result.append(a[0])
                hora += 30
                if (int(hora) == int(hora_inicial)):
                    result.append(a[0])
                if hora % 100 == 60:
                    hora += 40
                if (int(hora) == int(hora_inicial)):
                    result.append(a[0])
                duracao -= 1

    finalResult = []
    for i in result:
        if (int(i)!=int(idAulaToCheck)):
            finalResult.append(i) 
    if (finalResult==[]):
        query = """SELECT duracao FROM aula WHERE id=?"""
        cursor.execute(query, (idAulaToCheck,))
        duracaoAula = int(cursor.fetchone()[0])
        cursor.close()
        conn.close()
        isBloco = False
        for bloco in organizeBlocos(getSalaBlocos(ProjectNumber, sala), dia_semana):
            thisduracaoAula = duracaoAula
            hora = bloco[0]
            while thisduracaoAula > 1:
                #print(f"Hora: {hora} vs. HoraInicial: {hora_inicial}")
                if (int(hora) == int(hora_inicial)):
                    isBloco = True
                hora += 30
                if (int(hora) == int(hora_inicial)):
                    isBloco = True
                if hora % 100 == 60:
                    hora += 40
                if (int(hora) == int(hora_inicial)):
                    isBloco = True
                thisduracaoAula -= 1
        if isBloco:
            return [idAulaToCheck]
        else:
            return None
    else:
        return finalResult


def getAulaFromUCAndTime(ProjectNumber, hora_inicial, dia_semana, uc, idAulaToCheck):
    # Establish a connection to the database
    path = "Project" + str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    result = []
    for a in getUcHorario(ProjectNumber, uc):
        if (a["diaSemana"] == dia_semana):
            query = """SELECT duracao, horaInicial FROM aula WHERE id=?"""
            cursor.execute(query, (a[0],))
            resultado = cursor.fetchone()
            duracao = resultado[0]
            horaInicio = resultado[1]
            hora = horaInicio
            while duracao > 1:
                if (int(hora) == int(hora_inicial)):
                    result.append(a[0])
                hora += 30
                if (int(hora) == int(hora_inicial)):
                    result.append(a[0])
                if hora % 100 == 60:
                    hora += 40
                if (int(hora) == int(hora_inicial)):
                    result.append(a[0])
                duracao -= 1
    cursor.close()
    conn.close()
    finalResult = []
    for i in result:
        if (int(i)!=int(idAulaToCheck)):
            finalResult.append(i) 
    return finalResult

def getAulaFromDocenteAndTime(ProjectNumber, hora_inicial, dia_semana, docente, idAulaToCheck):
    # Establish a connection to the database
    #print("getAulaFromDocenteAndTime Docente: ", docente)
    path = "Project" + str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    result = []
    for a in getDocenteHorario(ProjectNumber, docente):
        if (a["diaSemana"] == dia_semana):
            query = """SELECT duracao, horaInicial FROM aula WHERE id=?"""
            cursor.execute(query, (a[0],))
            resultado = cursor.fetchone()
            duracao = resultado[0]
            horaInicio = resultado[1]
            hora = horaInicio
            while duracao > 1:
                if (int(hora) == int(hora_inicial)):
                    result.append(a[0])
                hora += 30
                if (int(hora) == int(hora_inicial)):
                    result.append(a[0])
                if hora % 100 == 60:
                    hora += 40
                if (int(hora) == int(hora_inicial)):
                    result.append(a[0])
                duracao -= 1
    finalResult = []
    for i in result:
        # print(f"This is the id: {i} as opposed to the idToCheck: {idAulaToCheck}" )
        if (int(i)!=int(idAulaToCheck)):
            finalResult.append(i) 
    if (finalResult == []):
        query = """SELECT duracao FROM aula WHERE id=?"""
        cursor.execute(query, (idAulaToCheck,))
        duracaoAula = int(cursor.fetchone()[0])
        isBloco = False
        cursor.close()
        conn.close()
        for bloco in organizeBlocos(getDocenteBlocos(ProjectNumber, docente), dia_semana):
            thisduracaoAula = duracaoAula
            hora = bloco[0]
            while thisduracaoAula > 1:
                #print(f"Hora: {hora} vs. HoraInicial: {hora_inicial}")
                if (int(hora) == int(hora_inicial)):
                    isBloco = True
                hora += 30
                if (int(hora) == int(hora_inicial)):
                    isBloco = True
                if hora % 100 == 60:
                    hora += 40
                if (int(hora) == int(hora_inicial)):
                    isBloco = True
                thisduracaoAula -= 1
        if isBloco:
            return [idAulaToCheck]
        else:
            return None
    else: 
        return finalResult
    
def getAulaFromTurmaAndTime(ProjectNumber, hora_inicial, dia_semana, turma, idAulaToCheck):
    # Establish a connection to the database
    path = "Project" + str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    result = []
    for a in getTurmaHorario(ProjectNumber, turma):
        if (a["diaSemana"] == dia_semana):
            query = """SELECT duracao, horaInicial FROM aula WHERE id=?"""
            cursor.execute(query, (a[0],))
            resultado = cursor.fetchone()
            duracao = resultado[0]
            horaInicio = resultado[1]
            hora = horaInicio
            while duracao > 1:
                if (int(hora) == int(hora_inicial)):
                    result.append(a[0])
                hora += 30
                if (int(hora) == int(hora_inicial)):
                    result.append(a[0])
                if hora % 100 == 60:
                    hora += 40
                if (int(hora) == int(hora_inicial)):
                    result.append(a[0])
                duracao -= 1
    finalResult = []
    # print(f"Turma: {turma} -> Result {result}")

    for i in result:
        # print(f"Result i: {i}")
        if (int(i)!=int(idAulaToCheck)):
            finalResult.append(i) 
    # print(f"finalResult: {finalResult}")
    if (finalResult == []):
        query = """SELECT duracao FROM aula WHERE id=?"""
        cursor.execute(query, (idAulaToCheck,))
        duracaoAula = int(cursor.fetchone()[0])
        isBloco = False
        cursor.close()
        conn.close()
        for bloco in organizeBlocos(getTurmaBlocos(ProjectNumber, turma), dia_semana):
            thisduracaoAula = duracaoAula
            hora = bloco[0]
            while thisduracaoAula > 1:
                #print(f"Hora: {hora} vs. HoraInicial: {hora_inicial}")
                if (int(hora) == int(hora_inicial)):
                    isBloco = True
                hora += 30
                if (int(hora) == int(hora_inicial)):
                    isBloco = True
                if hora % 100 == 60:
                    hora += 40
                if (int(hora) == int(hora_inicial)):
                    isBloco = True
                thisduracaoAula -= 1
        if isBloco:
            return [-1]
        else:
            return None
    else:
        return finalResult

# This function retrieves all classes for a given course and year and groups them by the class' shift (turno)
def getTurmasPorTurnoCursoAno(ProjectNumber, curso, ano):
    # Establish a connection to the database
    path = "Project" + str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    stmt = '''
        SELECT uc, turno, GROUP_CONCAT(turmas) as turmas
        FROM (
            SELECT uc.sigla AS uc, turno.numero AS turno, turmas.codigo AS turmas,
                COUNT(*) AS count,
                ROW_NUMBER() OVER (PARTITION BY uc.sigla, turmas.codigo ORDER BY COUNT(*) DESC) AS rn
            FROM turno
            JOIN turmas ON turno.idTurma = turmas.codigo
            JOIN curso ON turmas.idCurso = curso.abreviacao
            JOIN uc ON turno.idUC = uc.codigo
            WHERE curso.abreviacao = ? AND turmas.ano = ?
            GROUP BY uc.sigla, turno.numero, turmas.codigo 
        ) t
        WHERE rn = 1
        GROUP BY uc, turno
    '''

    # Execute the SQL statement and fetch all the rows
    cursor.execute(stmt, (curso, ano))
    result = cursor.fetchall()

    # Create a dictionary to store the classes by shift
    turmas_por_turno = {}
    turno_sets_counts = {}
    for row in result:
        turmas = row['turmas'].split(',')
        if row['uc'] not in turmas_por_turno:
            turmas_por_turno[row['uc']] = {}
        turno = row['turno']
        if turno not in turmas_por_turno[row['uc']]:
            turmas_por_turno[row['uc']][turno] = turmas
        else:
            turmas_por_turno[row['uc']][turno].extend(turmas)

    for uc in turmas_por_turno:
        turnos_set = frozenset(turmas_por_turno[uc].keys())
        turno_sets_counts[turnos_set] = turno_sets_counts.get(turnos_set, 0) + 1
    
    common_turnos = max(turno_sets_counts, key=turno_sets_counts.get)

    final_dict = {turno: [] for turno in common_turnos}
    for uc in turmas_por_turno:
        uc_turnos_set = set(turmas_por_turno[uc].keys())
        if uc_turnos_set == common_turnos:
            for turno in uc_turnos_set:
                final_dict[turno] = turmas_por_turno[uc][turno]
        else:
            for turno in uc_turnos_set:
                uc_string = sub(r'\(.*?\)', '', uc)
                final_dict[f"{uc_string} {turno}"] = turmas_por_turno[uc][turno]

    # Return the dictionary
    return final_dict

# This function retrieves the number of classes for a given course, year, and shift
def getNumeroTurmasPorTurnoAnoCurso(ProjectNumber, curso, ano):
    # Establish a connection to the database
    path = "Project" + str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # SQL statement to retrieve the data needed
    stmt = '''SELECT turno.numero AS myturno, COUNT(DISTINCT turmas.codigo) AS num_turmas
              FROM turno
              JOIN turmas ON turno.idTurma = turmas.codigo
              JOIN curso ON turmas.idCurso = curso.abreviacao
              WHERE curso.abreviacao = ? AND turmas.ano = ?
              GROUP BY turno.numero'''

    # Execute the SQL statement and fetch all the rows
    cursor.execute(stmt, (curso, ano))
    result = cursor.fetchall()

    # Create a dictionary to store the number of classes by shift
    num_turmas_por_turno = {row['myturno']: row['num_turmas'] for row in result}

    # Return the dictionary
    return num_turmas_por_turno

# This function retrieves the total number of classes for a given course and year
def getNumeroTurmasAno(ProjectNumber, curso, ano):
    # Establish a connection to the database
    path = "Project" + str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # SQL statement to retrieve the data needed
    stmt = '''SELECT COUNT(*) as num_turmas 
              FROM turmas 
              JOIN curso ON turmas.idCurso = curso.abreviacao
              WHERE curso.abreviacao = ? AND turmas.ano = ?'''
    # Execute the SQL statement and fetch one row
    cursor.execute(stmt, (curso, ano))
    result = cursor.fetchone()

    # Retrieve the number of classes and return it
    num_turmas = result['num_turmas']
    return num_turmas

def getDistribuicaoUC(ProjectNumber, uc_codigo):
    path = "Project" + str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
     # Query to retrieve the distribution of the given UC
    query = '''
        SELECT salas.tipo, turno.numero, aula.diaSemana, COUNT(*) AS num_aulas
        FROM aula
        JOIN aulaUC ON aula.id = aulaUC.idAula
        JOIN uc ON uc.codigo = aulaUC.idUC
        JOIN aulaSala ON aula.id = aulaSala.idAula
        JOIN salas ON salas.numero = aulaSala.idSala
        JOIN aulaTurmas ON aula.id = aulaTurmas.idAula
        JOIN turno ON turno.idTurma = aulaTurmas.idTurma AND turno.idUC = uc.codigo
        WHERE uc.codigo = ?
        GROUP BY salas.tipo, turno.numero, aula.diaSemana
    '''

    # Execute the query with the given UC code
    cursor.execute(query, (uc_codigo,))
    rows = cursor.fetchall()

    # Create the distribution dictionary
    distribution = {}

    for row in rows:
        tipo_sala = row[0]
        numero_turno = row[1]
        dia_semana = row[2]
        num_aulas = row[3]

        # Add the entry to the distribution dictionary
        if tipo_sala not in distribution:
            distribution[tipo_sala] = {}
        if numero_turno not in distribution[tipo_sala]:
            distribution[tipo_sala][numero_turno] = {}
        distribution[tipo_sala][numero_turno][dia_semana] = num_aulas

    # Close the database connection
    conn.close()

    return distribution

def getDocentesFromAnoFromCurso(ProjectNumber, abrevCurso, ano):
    # Connect to the database
    path = "Project" + str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Query the database for the professors in the given course and year
    cursor.execute('''SELECT DISTINCT d.numeroMecanografico, d.nome, d.abreviacao
                      FROM docentes d
                      JOIN aulaDocente ad ON d.numeroMecanografico = ad.idDocente
                      JOIN aulaTurmas at ON ad.idAula = at.idAula
                      JOIN turmas t ON at.idTurma = t.codigo
                      JOIN curso c ON t.idCurso = c.abreviacao
                      JOIN aula a ON at.idAula = a.id
                      WHERE c.abreviacao = ? AND t.ano = ?''', (abrevCurso, ano))

    # Get the query results
    docentes = cursor.fetchall()

    # Return the results
    return docentes

def getDocentesFromCurso(ProjectNumber, abrevCurso):
    # Connect to the database
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Query the database for the professors in the given course
    cursor.execute('''SELECT DISTINCT d.numeroMecanografico, d.nome, d.abreviacao
        FROM docentes d
        JOIN aulaDocente ad ON d.numeroMecanografico = ad.idDocente
        JOIN aulaTurmas at ON ad.idAula = at.idAula
        JOIN turmas t ON at.idTurma = t.codigo
        JOIN curso c ON t.idCurso = c.abreviacao
        WHERE c.abreviacao = ? ''', (abrevCurso,))

    # Get the query results
    result = cursor.fetchall()
    

    # Return the results
    return result

def getTurmasFromAnoCurso(ProjectNumber, abrevCurso, ano):
    # Connect to the database
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Query the database for the classes in the given course
    cursor.execute('''SELECT codigo FROM turmas 
              JOIN curso ON turmas.idCurso = curso.abreviacao
              WHERE curso.abreviacao = ? AND turmas.ano = ?''', (abrevCurso, ano))

    # Get the query results
    result = cursor.fetchall()
    
    turmas = []
    
    for turma in result:
        turmas.append(turma["codigo"])

    # Return the results
    return turmas

def getTurmasFromCurso(ProjectNumber, abrevCurso):
    # Connect to the database
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Query the database for the classes in the given course
    cursor.execute('''SELECT ano, codigo FROM turmas WHERE idCurso=?''', (abrevCurso,))

    # Get the query results
    turmas = cursor.fetchall()

    # Return the results
    return turmas


def getTurmasFromTurno(ProjectNumber, abreviacao_curso):
    # Connect to database
    path = "Project" + str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Execute query to get all distinct turmas (classes) from each turno (shift) for the given course
    stmt = '''SELECT DISTINCT t.numero AS numero_turno, GROUP_CONCAT(DISTINCT tu.idTurma) AS turmas 
              FROM turno t 
              JOIN turmaUC tu ON t.idTurma = tu.idTurma 
              JOIN uc u ON t.idUC = u.codigo 
              JOIN curso c ON u.idCurso = c.abreviacao 
              WHERE c.abreviacao = ? 
              GROUP BY t.numero;'''
    cursor.execute(stmt, (abreviacao_curso,))
    result = cursor.fetchall()
    
    # Return list of turmas for each turno
    return result

def getSalasPorAnoCurso(ProjectNumber, abrevCurso):
    # Connect to the database
    path = "Project" + str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Execute query to get the rooms used in classes for the given course
    stmt = '''SELECT DISTINCT salas.numero, salas.tipo, salas.capacidade, turmas.ano
              FROM aula
              JOIN aulaSala ON aula.id = aulaSala.idAula
              JOIN salas ON aulaSala.idSala = salas.numero
              JOIN aulaTurmas ON aula.id = aulaTurmas.idAula
              JOIN turmas ON aulaTurmas.idTurma = turmas.codigo
              JOIN curso ON turmas.idCurso = curso.abreviacao
              WHERE curso.abreviacao = ?'''
    cursor.execute(stmt, (abrevCurso,))
    result = cursor.fetchall()

    # Initialize dictionary to hold the result
    salas_por_ano = {}

    # Iterate through each row in the result set
    for row in result:
        sala_numero = row['numero']
        sala_tipo = row['tipo']
        sala_capacidade = row['capacidade']
        ano = row['ano']
        
        sala_dict = {
            "numero": sala_numero,
            "tipo": sala_tipo,
            "capacidade": sala_capacidade
        }

        # Add the sala to the corresponding year in the result dictionary
        if ano not in salas_por_ano:
            salas_por_ano[ano] = [sala_dict]
        else:
            salas_por_ano[ano].append(sala_dict)

    # Return the result dictionary
    return salas_por_ano

def getSalasFromCurso(ProjectNumber, abreviacao_curso):
    # Connect to database
    path = "Project" + str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Execute query to get all UCs (courses) for the given course
    stmt = '''SELECT DISTINCT numero, tipo, capacidade
              FROM salas 
              JOIN aulaSala ON salas.numero = aulaSala.idSala
              JOIN aulaUC ON aulaSala.idAula = aulaUC.idAula
              JOIN uc ON aulaUC.idUC = uc.codigo
              JOIN turmas ON uc.idCurso = turmas.idCurso
              WHERE turmas.idCurso = ?
              '''
    cursor.execute(stmt, (abreviacao_curso,))
    result = cursor.fetchall()

    # Extract the list of UC codes from the result set
    list_of_results = [row['numero'] for row in result]
    
    # Return list of UC codes
    return result

def getUCsFromCurso(ProjectNumber, abreviacao_curso):
    # Connect to database
    path = "Project" + str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Execute query to get all UCs (courses) for the given course
    stmt = '''SELECT DISTINCT codigo, nome, sigla
              FROM uc 
              JOIN curso ON uc.idCurso = curso.abreviacao 
              WHERE curso.abreviacao = ?'''
    cursor.execute(stmt, (abreviacao_curso,))
    result = cursor.fetchall()

    # Return list of UC codes
    return result

def getSalaHorarioAgrupado(ProjectNumber, numero, curso):
    # Connect to database
    path = "Project" + str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Execute query to get all aulas (lessons) for the given UC
    stmt = '''SELECT aula.id, aula.diaSemana, turmas.codigo, turmas.ano 
              FROM aula
              JOIN aulaSala ON aula.id = aulaSala.idAula
              JOIN aulaTurmas ON aula.id = aulaTurmas.idAula
              JOIN turmas ON aulaTurmas.idTurma = turmas.codigo
              WHERE aulaSala.idSala=? AND turmas.idCurso=?'''
    cursor.execute(stmt, (numero, curso,))
    result = cursor.fetchall()

    # Initialize dictionary to hold the result
    horario_sala = {}

    # Iterate through each aula in the result set and add it to the corresponding day and turma
    for row in result:
        aula_id = row['id']
        turma_codigo = row['codigo']
        ano = row['ano']

        # Execute query to get the details of the aula
        stmt2 = '''SELECT * FROM aula WHERE id=?'''
        cursor.execute(stmt2, (aula_id,))
        aula_result = cursor.fetchone()

        # Add the aula tuple to the corresponding year and aula in the result dictionary
        if ano not in horario_sala:
            horario_sala[ano] = {}

        if aula_result not in horario_sala[ano]:
            horario_sala[ano][aula_result] = [turma_codigo]
        else:
            horario_sala[ano][aula_result].append(turma_codigo)

    return horario_sala

def getUcHorarioAgrupado(ProjectNumber, codigo, curso):
    # Connect to database
    path = "Project" + str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Execute query to get all aulas (lessons) for the given UC
    stmt = '''SELECT aula.id, aula.diaSemana, turmas.codigo, turmas.ano 
              FROM aula
              JOIN aulaUC ON aula.id = aulaUC.idAula
              JOIN aulaTurmas ON aula.id = aulaTurmas.idAula
              JOIN turmas ON aulaTurmas.idTurma = turmas.codigo
              WHERE aulaUC.idUC=? AND turmas.idCurso=?'''
    cursor.execute(stmt, (codigo, curso,))
    result = cursor.fetchall()

    # Initialize dictionary to hold the result
    horario_uc = {}

    # Iterate through each aula in the result set and add it to the corresponding day and turma
    for row in result:
        aula_id = row['id']
        turma_codigo = row['codigo']
        ano = row['ano']

        # Execute query to get the details of the aula
        stmt2 = '''SELECT * FROM aula WHERE id=?'''
        cursor.execute(stmt2, (aula_id,))
        aula_result = cursor.fetchone()

        # Add the aula to the corresponding year and aula in the result dictionary
        if ano not in horario_uc:
            horario_uc[ano] = {}

        if aula_id not in horario_uc[ano]:
            horario_uc[ano][aula_result] = [turma_codigo]
        else:
            horario_uc[ano][aula_result].append(turma_codigo)

    return horario_uc
    

def getDocenteHorarioAgrupado(ProjectNumber, numeroMecanografico, curso):
    # Connect to database
    path = "Project" + str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Execute query to get all aulas (lessons) for the given docente (teacher)
    stmt = '''SELECT aula.id, aula.diaSemana, turmas.codigo, turmas.ano 
              FROM aula
              JOIN aulaDocente ON aula.id = aulaDocente.idAula
              JOIN aulaTurmas ON aula.id = aulaTurmas.idAula
              JOIN turmas ON aulaTurmas.idTurma = turmas.codigo
              WHERE aulaDocente.idDocente=? AND turmas.idCurso=?'''
    cursor.execute(stmt, (numeroMecanografico, curso,))
    result = cursor.fetchall()

    # Initialize dictionary to hold the result
    horario_docente = {}

    # Iterate through each aula in the result set and add it to the corresponding day and turma
    for row in result:
        aula_id = row['id']
        turma_codigo = row['codigo']
        ano = row['ano']

        # Execute query to get the details of the aula
        stmt2 = '''SELECT * FROM aula WHERE id=?'''
        cursor.execute(stmt2, (aula_id,))
        aula_result = cursor.fetchone()

        # Add the aula to the corresponding year and aula in the result dictionary
        if ano not in horario_docente:
            horario_docente[ano] = {}

        if aula_id not in horario_docente[ano]:
            horario_docente[ano][aula_result] = [turma_codigo]
        else:
            horario_docente[ano][aula_result].append(turma_codigo)

    return horario_docente

def getTurmasFromAula(ProjectNumber, aulaId, curso):
    # Connect to database
    path = "Project" + str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Execute query to get all turmas for the given aula
    stmt = '''SELECT idTurma, ano FROM aulaTurmas JOIN turmas ON aulaTurmas.idTurma = turmas.codigo WHERE idAula=? AND turmas.idCurso=?'''
    cursor.execute(stmt, (aulaId, curso,))
    result = cursor.fetchall()
    turmas_dict = {}

    for row in result:
        idTurma = row['idTurma']
        ano = row['ano']
        if ano in turmas_dict:
            turmas_dict[ano].append(idTurma)
        else:
            turmas_dict[ano] = [idTurma]

    # Return dictionary of turmas codigos for the given aula
    return turmas_dict
    

def getDocenteHorario(ProjectNumber, numeroMecanografico): 
    # Connect to database
    path = "Project" + str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Query to get all idAula2 values from aulasSimultaneas table
    stmt_exclude = '''SELECT aula2 FROM aulasSimultaneas'''
    cursor.execute(stmt_exclude)
    excluded_aulas = cursor.fetchall()
    excluded_aulas_set = {row['aula2'] for row in excluded_aulas}
    
    # Execute query to get all aulas (lessons) for the given docente (teacher)
    stmt = '''SELECT idAula FROM aulaDocente WHERE idDocente=?'''
    cursor.execute(stmt, (numeroMecanografico,))
    result = cursor.fetchall()
    list_of_results = []
              
    # Iterate through each aula id in the result set and execute a query to get the aula details
    for row in result:
        if row['idAula'] is not None and row['idAula'] not in excluded_aulas_set:
            stmt2 = '''SELECT * FROM aula WHERE id=?'''
            cursor.execute(stmt2, (row['idAula'],))
            newresult = cursor.fetchall()
            for row2 in newresult:
                list_of_results.append(row2)
                
    # Return list of aula details for the given docente
    return list_of_results     

def getTurmaHorario(ProjectNumber, nomeTurma): 
    # This function retrieves all the classes in a specific course
    # given the project number and the name of the course.
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Select all the class IDs associated with the course.
    stmt = '''SELECT idAula FROM aulaTurmas WHERE idTurma=?'''
    cursor.execute(stmt, (nomeTurma,))
    result = cursor.fetchall()
    list_of_results = []
              
    for row in result:
        if row['idAula'] is not None:
            # Select all the information for each class based on its ID.
            stmt2 = '''SELECT * FROM aula WHERE id=?'''
            cursor.execute(stmt2, (row['idAula'],))
            newresult = cursor.fetchall()
            for row2 in newresult:
                list_of_results.append((row2))
    return list_of_results     

def getSalaHorario(ProjectNumber, numeroSala): 
    # This function retrieves all the classes scheduled in a specific room
    # given the project number and the room number.
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Query to get all idAula2 values from aulasSimultaneas table
    stmt_exclude = '''SELECT aula2 FROM aulasSimultaneas'''
    cursor.execute(stmt_exclude)
    excluded_aulas = cursor.fetchall()
    excluded_aulas_set = {row['aula2'] for row in excluded_aulas}
    
    # Select all the class IDs scheduled in the room.
    stmt = '''SELECT idAula FROM aulaSala WHERE idSala=?'''
    cursor.execute(stmt, (numeroSala,))
    result = cursor.fetchall()
    list_of_results = []
              
    for row in result:
        if row['idAula'] is not None and row['idAula'] not in excluded_aulas_set:
            # Select all the information for each class based on its ID.
            stmt2 = '''SELECT * FROM aula WHERE id=?'''
            cursor.execute(stmt2, (row['idAula'],))
            newresult = cursor.fetchall()
            for row2 in newresult:
                list_of_results.append(row2)
    return list_of_results


def getUcHorario(ProjectNumber, codUc): 
    # This function retrieves all the classes for a specific course
    # given the project number and the course code.
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Select all the class IDs associated with the course.
    stmt = '''SELECT idAula FROM aulaUC WHERE idUC=?'''
    cursor.execute(stmt, (codUc,))
    result = cursor.fetchall()
    list_of_results = []
              
    for row in result:
        if row['idAula'] is not None :
            # Select all the information for each class based on its ID.
            stmt2 = '''SELECT * FROM aula WHERE id=?'''
            cursor.execute(stmt2, (row['idAula'],))
            newresult = cursor.fetchall()
            for row2 in newresult:
                list_of_results.append(row2)
    return list_of_results


def getDocenteBlocos(ProjectNumber, numeroMecanografico): 
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
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
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
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
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
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

def getAulasFromTurno(ProjectNumber, turno):
    manchaTurmas = {} 
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
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
        
def getNumYearsFromCurso(ProjectNumber, curso):
    path = "Project"+str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    stmt = '''SELECT COUNT(DISTINCT ano) AS num_years FROM turmas WHERE idCurso=?'''
    cursor.execute(stmt, (curso,))
    result = cursor.fetchone()
    return result['num_years']

def getCursos(ProjectNumber):
    path = "Project" + str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    stmt = '''SELECT DISTINCT curso.abreviacao AS curso_nome FROM curso'''
    cursor.execute(stmt)
    result = cursor.fetchall()
    cursos = [row['curso_nome'] for row in result]  # Access the 'curso_nome' column value for each row
    return cursos

def getAnoFromUcCurso(ProjectNumber, curso, uc):
    path = "Project" + str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    stmt = '''SELECT DISTINCT turmas.ano AS uc_year FROM turmas
            INNER JOIN turmaUC ON turmas.codigo = turmaUC.idTurma
            INNER JOIN uc ON turmaUC.idUC = uc.codigo
            WHERE uc.codigo=? AND turmas.idCurso=?'''
    cursor.execute(stmt, (uc, curso,))
    result = cursor.fetchall()
    return [row['uc_year'] for row in result]

def getSemanasFromCursoAno(ProjectNumber, curso, ano):
    path = "Project" + str(ProjectNumber)
    conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    stmt = '''SELECT DISTINCT semanaInicial, semanaFinal FROM aula
            JOIN aulaUC on aulaUC.idAula = aula.id
            JOIN uc ON aulaUC.idUC = uc.codigo
            JOIN aulaTurmas on aulaTurmas.idAula = aula.id
            JOIN turmas ON aulaTurmas.idTurma = turmas.codigo
            JOIN curso ON turmas.idCurso = curso.abreviacao
            WHERE curso.abreviacao=? AND turmas.ano=?'''
    cursor.execute(stmt, (curso, ano,))
    result = cursor.fetchall()
    return [(row['semanaInicial'], row['semanaFinal']) for row in result]

