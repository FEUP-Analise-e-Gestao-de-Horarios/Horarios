from ctypes import sizeof
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from bs4 import BeautifulSoup
import requests
import re
import sqlite3
from datetime import datetime
import os
from .directories import createDir
import operator
import time
import shutil
from core.models import Project
import bleach
import concurrent.futures
import sys
import linecache
import traceback

turnosMap = {}

max_workers = 4  # Set the maximum number of parallel threads
executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

# table_to_matrix
#
# receives an html table element
# and converts to a matrix
# the matrix is composed of <td> elements
# it repeats the elements so they occupy the same number of rows and columns
# as their rowspans and colspans
# makes it easier to map aula date and duration
def table_to_matrix(table):
    # Find all rows in the table
    rows = table.find_all('tr')
    rows = rows[3:]
    
    # Determine the number of rows and columns in the table
    num_rows = len(rows)
    num_cols = max([len(row.find_all(['td', 'th'])) for row in rows])
    
    # Create a matrix to store the table data
    matrix = [[None for _ in range(num_cols)] for _ in range(num_rows)]
    # Iterate over each cell in the table
    for i, row in enumerate(rows):
        cells = row.find_all('td')
        j = 0
        for cell in cells:
            # Find the rowspan and colspan of the cell
            rowspan = int(cell.get('rowspan', 1))
            colspan = int(cell.get('colspan', 1))
            
            # Insert the data into the matrix
            while matrix[i][j] is not None:
                j += 1
            for k in range(rowspan):
                for l in range(colspan):
                    matrix[i+k][j+l] = cell
            
            # Move the column index to the next available cell
            j += colspan
    return matrix

# get_index
#
# receives a <td> html element and the matrix
# searchs for it in the matrix, returning the column in which it was found
# when it is found, all of its positions are changed to null
def get_index(item, matrix):
    for i, row in enumerate(matrix):
        for j, td in enumerate(row):
            if item == td:
                matrix[i][j] = None
                rowspan = item.get('rowspan')
                if rowspan is None:
                    rowspan = "1"
                for y in range(i+1, i+int(rowspan)):
                    matrix[y][j]=None
                return j, matrix

# getWeekDay
#
# receives the index day number and returns the corresponding weekday
def getWeekDay(index):
    match index:
        case 1:
            return 'Segunda'
        case 2:
            return 'Terça'
        case 3:
            return 'Quarta'
        case 4:
            return 'Quinta'
        case 5:
            return 'Sexta'
        case 6:
            return 'Sábado'
        case other:
            return None

# get_code
#
# parses a page for the code of a docente or a uc
def get_code(req, tipo):
    soup = BeautifulSoup(req.content, "html.parser")
    table = soup.find('center').find('table')
    cabecalho = table.find('td', {'class':'cabtitulo'})
    text = cabecalho.text
    temp = re.findall(r'\d+', text)

    match tipo:
        case 'docente':
            return list(map(int, temp))[0]
        case 'uc':
            # falta boscar a sigla
            return list(map(int, temp))[3]
        case other:
            return None

# get_dia_from_index
#
# receives the index and a spanMap
# maps the currect index to the correct day number
def get_dia_from_index(index, spanMap):
    if index == 1:
        return 'Segunda'
    count = 0
    for (dia, span) in spanMap.items():
        count += int(span)
        if count >= index:
            return dia

#parse_horarios_vermelhos
#
# receives the page request 
# and returns a list with the relevant attributes
def parse_horario_vermelhos(req):
    lista = []
    soup = BeautifulSoup(req.content, "html.parser")
    vermelhos = soup.find_all('td', {'class':'td_vermelha'})
    table = soup.find('center').find('table', {'class':'tabela_principal'})
    
    matrix = table_to_matrix(table)

    if len(vermelhos) == 0:
        return lista

    dias = vermelhos[0].parent.parent.findChildren(recursive=False)[3]
    diaSpans = {}
    
    for i, dia in enumerate(dias.findChildren()):
        if i == 0: continue
        diaSpans[dia.text] = dia.get('colspan')

    for item in vermelhos:
        pai = item.parent
        hora = int(pai.findChild().text.replace(':', ''))
        index, matrix = get_index(item, matrix)
        dia = get_dia_from_index(index, diaSpans)
        lista.append((dia, hora))

    return lista

#some of the tipologias found:
# 21 - Teroico-Pratica
# 19 - Teorica
# 16 - Pratica
# 14 - O
# 18 - S
# 17 - PL
# 20 - TC
# 15 - OT

#no typology over 21 found, so consider anything from td_tipologia_1 to td_tipologia_21
tipologias = ['td_tipologia_' + str(id) for id in range(1, 22)]

#parse_horario
#
# receives the page request and the UC code
# parses the schedule and returns a list with the relevant attributes
def parse_horario(req, cod_uc):
    turnos = []
    lista = []
    soup = BeautifulSoup(req.content, "html.parser")
    aulas = soup.find('center').find_all('td', {'class':tipologias})
    semanas = soup.find('td', {'class' : 'cabtitulo'}).contents
    semanas = str(semanas[-1])
    semanaIniEFin = semanas.split("Semanas: ")[1]
    if (" - " in semanaIniEFin):
        semanaIni = semanaIniEFin.split(" - ")[0]
        semanaFin = semanaIniEFin.split(" - ")[1]
    else:
        semanaIni = semanaIniEFin.split(" - ")[0]
        semanaFin = semanaIni


    table = soup.find('center').find('table', {'class':'tabela_principal'})
    matrix = table_to_matrix(table)

    
    dias = aulas[0].parent.parent.findChildren(recursive=False)[3]
    diaSpans = {}
    
    for i, dia in enumerate(dias.findChildren()):
        if i == 0: continue
        diaSpans[dia.text] = dia.get('colspan')

    for aula in aulas: 
        count = 0
        att = {}
        if aula.get('class')[0] == 'td_tipologia_19':
            att['isTeorica'] = True
        else:
            att['isTeorica'] = False

        att['span'] = aula.get('rowspan')
        pattern = r'\[(.*?)\]'
        matches = re.findall(pattern, aula.text)
        #print(f"Cod_UC: {cod_uc} + Matches Length: {len(matches)} + Matches: {matches}")
        if (len(matches) > 2): 
            att['salas'] = matches[2]
        else: 
            att['salas'] = "Online"
        att['turmas'] = matches[0].split('; ')

        tempdocentes = matches[1].replace('(', '').replace(')', '').split('; ')
        att['semanaIni'] = semanaIni
        att['semanaFin'] = semanaFin
        #print(f"Cod_UC: {cod_uc} + Lista {lista}")
        docentes_dict = soup.findAll('table')[3].findAll('tr')[2:]
        for i in range(len(docentes_dict)):
            docentes_dict[i] = str(docentes_dict[i])
        result = {}

        # Loop through each element in the list
        for item in docentes_dict:
            # Extract the text between the <td> tags
            abrevs = item.split('<td align="left" valign="middle">')[2]
            abrevs = abrevs.split('</td>')[0]
            codes = item.split('<td align="left" valign="middle">')[3]
            codes = codes.split('</td>')[0]

            if abrevs not in result:
                result[abrevs] = [codes]
            else:
                result[abrevs].append(codes)
            # If there are three elements, assume it's the name, code, and value
        listadedocentes = []
        for i in tempdocentes:
            #print(f"Docente: {i} and Result: {result[i]} and Len: {len(result[i])}")
            if (len(result[i])==1):
                listadedocentes.append(result[i][0])
            else:
                listadedocentes.append(result[i][count])
                count += 1


        att['docentes'] = listadedocentes
        
        if (att['isTeorica']):
            turnos = att['turmas']
            if cod_uc in turnosMap: #se já existe esta UC
                if turnos not in turnosMap[cod_uc].values(): # se não existe este turno
                   numeroTurno = max(turnosMap[cod_uc].keys())
                   turnosMap[cod_uc][numeroTurno+1] = turnos
                   dicionario = turnosMap[cod_uc]
                   chaves_ordenadas = sorted(dicionario, key=lambda chave: dicionario[chave])
                   del turnosMap[cod_uc]
                   turnosMap[cod_uc] = {}
                   aux = 1
                   for chave in chaves_ordenadas:
                       turnosMap[cod_uc][aux] = dicionario[chave]
                       aux = aux+1
            else:
                turnosMap[cod_uc] = {1: turnos}

        pai = aula.parent
        att['hora'] = int(pai.findChild().text.replace(':', ''))
        index, matrix = get_index(aula, matrix)
        att['dia'] = get_dia_from_index(index, diaSpans)
        lista.append(att)    
    return lista


# parse_docentes
#
# parses all docentes in the sidebar
# parses their schedule page for the relevant attributes
# and the list of red block attributes
def parse_docentes(docentes):
    children = docentes.find('ul').findChildren(recursive=False)
    for child in children:
        content = child.find('ul').find_all('li', recursive=False)
        k = 0
        for i in content:
            a = i.find('a', recursive=False)
            semanas = str(a.contents).split("'")[1]
            semana = semanas.split(" - ")
            semanaInicio = semana[0].split(" ").pop()
            if len(semana) != 1:
                semanaFim = semana.pop()
            else:
                semanaFim = semanaInicio
            link = a['href']
            req = requests.get(paginas+link)
            vermelho = parse_horario_vermelhos(req)
            #Se ainda não tiver recolhido o nome, sigla e codigo
            if (k == 0):
                web_s = req.content
                soup = BeautifulSoup(web_s, "html.parser")
                content = soup.find('td', {'class' : 'cabtitulo'}).contents
                content = str(content)
                if ('"' in content):
                    first = content.split("\"")[1]
                    sigla = content.split("<br/>, '")[1].split("'")[0]
                    if (sigla in first):
                        nome = first[len(sigla):]
                    else:
                        nome = ""
                    codigo = content.split("<br/>, '")[2].split("'")[0]
                else:
                    content = content.split("', <br/>, '")
                    sigla = content[1].split("'")[0]
                    if (sigla in content[0]):
                        nome = content[0][len(sigla)+2:]
                    else:
                        nome = ""
                    codigo = content[2].split("'")[0]
                if (' - ' in nome):
                    nome = nome[3:]
                if (nome == ""):
                    nome = sigla
                nome = re.sub(r'[^\w\s]', '', nome)
                k = 1
            for (day, hour) in vermelho:
                stmtB = '''INSERT INTO blocosVermelhos (hora, diaSemana) VALUES (?, ?)'''
                cursor.execute(stmtB, (hour, day,))
                conn.commit()

                
                
                    
                stmtCounter = '''SELECT COUNT(*) FROM blocosVermelhos'''
                counter = cursor.execute(stmtCounter).fetchone()[0]

                stmtT = '''INSERT INTO blocoDocente (idBloco, idDocente) VALUES (?, ?)'''
                cursor.execute(stmtT, (counter, codigo))
                conn.commit()

                
                
        stmt = '''INSERT INTO docentes (numeroMecanografico, nome, abreviacao) VALUES (?, ?, ?)'''
        cursor.execute(stmt, (codigo, nome, sigla,))
        conn.commit()

    return

def parse_cursos(cursos):
    allCursos = set()
    for curso in cursos:
        info = curso.find('a').contents
        abreviatura = info[0].split(' - ')[0]
        nome = info[0].split(' - ', 1)[1]
        allCursos.add((nome, abreviatura))
    return allCursos

# parse_turmas
#
# parses all turmas in the sidebar
# parses their schedule page for the relevant attributes
# and the list of red block attributes
def parse_turmas(turmas):
    children = turmas.find('ul').findChildren(recursive = False)
    allCursos = parse_cursos(children)
    for child in children: 
        idCurso = child.find('a').contents
        idCursoStr = idCurso[0].split(' - ')[0]
        anos = child.find('ul').findChildren(recursive = False)
        for ano in anos:
            numeroAno = ano.find('a').contents
            numeroStr = numeroAno[0]
            numeroDois = numeroStr.split(" ")[1]
            plano_turmas = ano.find('ul').find('li')
            turmas = plano_turmas.find('ul')
            for turma in turmas.findChildren(recursive = False):
                str_nome = turma.find('a').contents
                nome = str(str_nome).split("'")[1]
                stmt = '''INSERT INTO turmas (idCurso, ano, codigo) VALUES (?, ?, ?)'''
                cursor.execute(stmt, (idCursoStr, numeroDois, nome))
                conn.commit()

                semanasLi = turma.find('ul').find_all('li')
                for thisSemana in semanasLi:
                    a = thisSemana.find('a', recursive=False)
                    semanas = str(a.contents).split("'")[1]
                    semana = semanas.split(" - ")
                    semanaInicio = semana[0].split(" ").pop()
                    if len(semana) != 1:
                        semanaFim = semana.pop()
                    else:
                        semanaFim = semanaInicio
                    link = a['href']
                    req = requests.get(paginas+link)
                    vermelho = parse_horario_vermelhos(req)
                    for (day, hour) in vermelho:
                        stmtB = '''INSERT INTO blocosVermelhos (hora, diaSemana) VALUES (?, ?)'''
                        cursor.execute(stmtB, (hour, day,))
                        conn.commit()
                        
                        stmtCounter = '''SELECT COUNT(*) FROM blocosVermelhos'''
                        counter = cursor.execute(stmtCounter).fetchone()[0]

                        stmtT = '''INSERT INTO blocoTurma (idBloco, idTurma) VALUES (?, ?)'''
                        cursor.execute(stmtT, (counter, nome))
                        conn.commit()

                        
                        

    for (nomeC, abrev) in allCursos:
        stmtCurs = '''INSERT INTO curso(designacao, abreviacao) VALUES(?,?)'''
        cursor.execute(stmtCurs, (nomeC, abrev,))
        conn.commit()
    return

def parse_uc_link(req):
    web_s = req.content
    soup_links = BeautifulSoup(web_s, "html.parser")
    header = soup_links.find('body').find('center').find('table').find('tr')
    info = header.find('td').find('table').find('tr').find('td', {'class': 'cabtitulo'}).contents
    newInfo = [item for item in info if not str(item).startswith("<br/>")]
    curso = newInfo[0].split(" - ")[0]
    sigla = newInfo[1].split("Sigla: ")[1]
    
    codigo = newInfo[2].split("Código: ")[1]
    return (sigla, codigo, curso)


# parse_ucs
#
# parses all ucs in the sidebar
# parses their schedule page for the relevant attributes
# the list of aulas attributes
# and the list of red block attributes
# 
# when parsing the schedule, it makes sure that the L.EIC and M.EIC courses are parsed
# otherwise the parse fails
# any other course may fail and the parse continues
def parse_ucs(ucs):
    children = ucs.find('ul').findChildren(recursive = False)
    count = 0
    for child in children:
        count += 1  
        li = child.find('ul').find('li')
        content = child.find('a').contents
        ucs = str(content).split("'")[1]
        if (' - ' in ucs):
            cod_uc = ucs.split(' - ', 1)[0]
            name_uc = ucs.split(' - ', 1)[1]
        else:
            cod_uc = ucs.split('- ', 1)[0]
            name_uc = ucs.split('- ', 1)[1]
        semana_content = li.find('a').contents
        semana_link = li.find('a')['href']

        req = requests.get(paginas+semana_link)
        (sigla, codigo, curso) = parse_uc_link(req)
        for i, char in enumerate(curso):
            if char.isdigit():
                curso = curso[:i]
        
        stmt = '''INSERT INTO uc (codigo, idCurso, nome, sigla, codOcorrencia) VALUES (?, ?, ?, ?, ?)'''
        cursor.execute(stmt, (cod_uc, curso, name_uc, sigla, codigo,))
        conn.commit()

        #Semanas das UCs
        lis = child.find('ul').find_all('li')
        for i, li in enumerate(lis):
            semana_content = li.find('a').contents
            semana_link = li.find('a')['href']
            semana = str(semana_content).split("'")[1]
            dates = semana.split(" ", 1)[1]
            semanas = str(dates).split(" - ")
            str_semanainicial = semanas[0]
            str_semanafinal = semanas[-1]
            date_format = '%d/%m/%Y'
            date_obj_fst = datetime.strptime(str_semanainicial, date_format).date()
            sqlite_date_ini = date_obj_fst.strftime('%d/%m/%Y')
            date_obj_snd = datetime.strptime(str_semanafinal, date_format).date()
            sqlite_date_fin = date_obj_snd.strftime('%d/%m/%Y')

            req = requests.get(paginas+semana_link)
            (sigla, codigo, uc_nome) = parse_uc_link(req)

            vermelhos = parse_horario_vermelhos(req)
            for (day, hour) in vermelhos:
                stmtB = '''INSERT INTO blocosVermelhos (hora, diaSemana) VALUES (?, ?)'''
                cursor.execute(stmtB, (hour, day,))
                conn.commit()
                
            if (curso != "M.EIC" and curso != "L.EIC"):
                try:
                    horario = parse_horario(req, cod_uc)
                    for aula in horario:
                        isTeorica = aula['isTeorica']
                        duracao = aula['span']
                        salas = aula['salas']
                        turmas = aula['turmas']
                        docentes = aula['docentes']
                        hora = aula['hora']
                        dia = aula['dia']
                        semanaIni = aula['semanaIni']
                        semanaFin = aula['semanaFin']


                        stmtC = '''INSERT INTO aula (horaInicial, duracao, diaSemana, teorico, semanaInicial, semanaFinal) VALUES (?, ?, ?, ?, ?, ?)'''
                        cursor.execute(stmtC, (hora, duracao, dia, isTeorica, semanaIni, semanaFin,))
                        conn.commit()

                        stmtCounter = '''SELECT COUNT(*) FROM aula'''
                        counter = cursor.execute(stmtCounter).fetchone()[0]

                        stmtAUC = '''INSERT INTO aulaUC (idAula, idUC) VALUES (?, ?)'''
                        cursor.execute(stmtAUC, (counter, cod_uc,))
                        conn.commit()

                        for docente in docentes:
                            stmtADC = '''INSERT INTO aulaDocente (idAula, idDocente) VALUES (?, ?)'''
                            cursor.execute(stmtADC, (counter, docente,))
                            conn.commit()

                        for turma in turmas: 
                            stmtAT = '''INSERT INTO aulaTurmas (idAula, idTurma) VALUES (?, ?)'''
                            cursor.execute(stmtAT, (counter, turma,))
                            conn.commit()

                            stmtChecker = '''SELECT * FROM turmaUC WHERE idTurma=? AND idUC=?'''
                            cursor.execute(stmtChecker, (turma, cod_uc,))
                            result=cursor.fetchall()
                            if (len(result) == 0):
                                stmtTUC = '''INSERT INTO turmaUC (idTurma, idUC) VALUES (?, ?)'''
                                cursor.execute(stmtTUC, (turma, cod_uc,))
                                conn.commit()
                            
                        for sala in salas.split(';'): 
                            stmtAS = '''INSERT INTO aulaSala (idAula, idSala) VALUES (?, ?)'''
                            cursor.execute(stmtAS, (counter, sala,))
                            conn.commit()
                except:
                    print(traceback.format_exc())
                    continue
            else:
                horario = parse_horario(req, cod_uc)
                for aula in horario:
                    isTeorica = aula['isTeorica']
                    duracao = aula['span']
                    salas = aula['salas']
                    turmas = aula['turmas']
                    docentes = aula['docentes']
                    hora = aula['hora']
                    dia = aula['dia']
                    semanaIni = aula['semanaIni']
                    semanaFin = aula['semanaFin']

                    stmtC = '''INSERT INTO aula (horaInicial, duracao, diaSemana, teorico, semanaInicial, semanaFinal) VALUES (?, ?, ?, ?, ?, ?)'''
                    cursor.execute(stmtC, (hora, duracao, dia, isTeorica, semanaIni, semanaFin,))
                    conn.commit()

                    stmtCounter = '''SELECT COUNT(*) FROM aula'''
                    counter = cursor.execute(stmtCounter).fetchone()[0]

                    stmtAUC = '''INSERT INTO aulaUC (idAula, idUC) VALUES (?, ?)'''
                    cursor.execute(stmtAUC, (counter, cod_uc,))
                    conn.commit()
                    
                    for docente in docentes:
                        stmtADC = '''INSERT INTO aulaDocente (idAula, idDocente) VALUES (?, ?)'''
                        cursor.execute(stmtADC, (counter, docente,))
                        conn.commit()

                    for turma in turmas: 
                        stmtAT = '''INSERT INTO aulaTurmas (idAula, idTurma) VALUES (?, ?)'''
                        cursor.execute(stmtAT, (counter, turma,))
                        conn.commit()

                        stmtChecker = '''SELECT * FROM turmaUC WHERE idTurma=? AND idUC=?'''
                        cursor.execute(stmtChecker, (turma, cod_uc,))
                        result=cursor.fetchall()
                        if (len(result) == 0):
                            stmtTUC = '''INSERT INTO turmaUC (idTurma, idUC) VALUES (?, ?)'''
                            cursor.execute(stmtTUC, (turma, cod_uc,))
                            conn.commit()
                        
                    for sala in salas.split(';'): 
                        stmtAS = '''INSERT INTO aulaSala (idAula, idSala) VALUES (?, ?)'''
                        cursor.execute(stmtAS, (counter, sala,))
                        conn.commit()
    return

# parse_salas
#
# parses all salas in the sidebar
# parses their schedule page for the relevant attributes
# and the list of red block attributes
def parse_salas(salas):
    children = salas.find('ul').findChildren(recursive=False)
    for child in children:
        a_list = child.find_all('a', {'class':"timetable-link"})
        content = child.find('a').contents
        if ("__cf_email__" in str(content)):
            content = ['EaD']
        #print(f"Child: {child} \n Content: {str(content)}")
        sala = str(content).split("'")[1]
        with open("parser/Salas.txt", "r") as file:
            alreadyInserted = False
            for line in file:
                if sala in line:
                    alreadyInserted = True
                    tipo, capacidade = line.strip().split(" - ")[0], line.strip().split(" - ")[-1]
                    if tipo == 'Anf':
                        if '.' in capacidade:
                            capacidade = capacidade[-2:]
                        tamanhoComp = 'N/A'
                    elif tipo == 'PCs':
                        if capacidade == 'Grandes':
                            tamanhoComp = '> 21'
                        elif capacidade == 'Media20':
                            capacidade = 'Media'
                            tamanhoComp = '20'
                        elif capacidade == 'Media16':
                            capacidade = 'Media'
                            tamanhoComp = '16'
                        else:
                            tamanhoComp = '< 15'
                    else:
                        tamanhoComp = 'N/A'
                    stmt = '''INSERT INTO salas(numero, tipo, capacidade, tamanhoComp) VALUES (?, ?, ?, ?)'''
                    cursor.execute(stmt, (sala, tipo, capacidade, tamanhoComp,))
                    conn.commit() 
                    
            if not alreadyInserted: # If already in Database
                stmt = '''INSERT INTO salas(numero, tipo, capacidade, tamanhoComp) VALUES (?, ?, ?, ?)'''
                cursor.execute(stmt, (sala, "Desconhecido", "Desconhecido", "Desconhecido",))
                conn.commit()     

                
                
        for a in a_list:
            semanas = str(a.contents).split("'")[1]
            semana = semanas.split(" - ")
            semanaInicio = semana[0].split(" ").pop()
            if len(semana) != 1:
                semanaFim = semana.pop()
            else:
                semanaFim = semanaInicio
            
            link = a.get('href')
            req = requests.get(paginas+link)
            vermelhos = parse_horario_vermelhos(req)
            for (day, hour) in vermelhos:
                stmtB = '''INSERT INTO blocosVermelhos (hora, diaSemana) VALUES (?, ?)'''
                cursor.execute(stmtB, (hour, day,))
                conn.commit()
                
                stmtCounter = '''SELECT COUNT(*) FROM blocosVermelhos'''
                counter = cursor.execute(stmtCounter).fetchone()[0]

                stmtT = '''INSERT INTO salaBloco (idBloco, idSala) VALUES (?, ?)'''
                cursor.execute(stmtT, (counter, sala))
                conn.commit()   
    return


def parse_turnos():
    for uc in turnosMap:
        for number in turnosMap[uc]:
            for turno in turnosMap[uc][number]:
                if (isinstance(turno, list)):
                    for turma in turno:
                        stmtS = '''SELECT * FROM turno WHERE idTurma=? AND idUC=?'''
                        cursor.execute(stmtS, (turma, uc))
                        result = cursor.fetchall()
                        if (len(result)==0):
                            stmtT = '''INSERT INTO turno (numero, idTurma, idUC) VALUES (?, ?, ?)'''
                            cursor.execute(stmtT, (number, turma, uc))
                            conn.commit()   

                else:
                    stmtS = '''SELECT * FROM turno WHERE idTurma=? AND idUC=?'''
                    cursor.execute(stmtS, (turno, uc))
                    result = cursor.fetchall()
                    if (len(result)==0):
                        stmtT = '''INSERT INTO turno (numero, idTurma, idUC) VALUES (?, ?, ?)'''
                        cursor.execute(stmtT, (number, turno, uc))
                        conn.commit()   


def fix_turmas_without_turnos():
    # Get the list of turmas from turmaUC that are not present in turnos
    query = '''
        SELECT tu.idTurma, tu.idUC
        FROM turmaUC tu
        LEFT JOIN turno tn ON tu.idTurma = tn.idTurma
        WHERE tn.idTurma IS NULL
    '''
    cursor.execute(query)
    missing_turmas = cursor.fetchall()

    # Create entries in turnos for each missing turma
    for turma in missing_turmas:
        idTurma, idUC = turma
        query = '''
            INSERT INTO turno (numero, idTurma, idUC)
            VALUES (0, ?, ?)
        '''
        cursor.execute(query, (idTurma, idUC))
        
    # Commit the changes and close the connection
    conn.commit()
    conn.close()
    

# parse
#
# Post Ajax request handler function
#
# starts a new project parse
# starts a new thread from a pool, if available
def parse(request):    
    if (not request.user.is_authenticated):
        return JsonResponse({"error": "User is not authenticated"}, status=401)
    
    if request.method != "POST" and not request.is_ajax():
        return JsonResponse({"error": "Invalid request"}, status=400)

    if isinstance(executor, concurrent.futures.ThreadPoolExecutor):
        active_workers = executor._work_queue.qsize()
    else:
        active_workers = 0

    if active_workers >=5:
        return JsonResponse({"error": "Número máximo de parses simultâneos excedidos. Por favor espere um pouco antes de tentar novamente."}, status=423)
    
    # run_parser
    #
    # parser function to be ran in the thread
    # gets the page url and the project name from the Post request
    # creates the project entry in the database
    # creates the project directory
    # creates the connection to the general_database
    # calls the other parse functions
    # copies the contents of the general_database to the intial_database
    # marks the the project as parsed
    # 
    # in case the parsing fails for any reason, the database entry is removed and the directory is deleted

    def run_parser():
        try:
            global conn
            global cursor
            global paginas

            paginas = bleach.clean(request.POST.get("paginas"))
            name = bleach.clean(request.POST.get("name"))
            
            path, projId = createDir(request.user.pk, name)

            proj = Project.objects.get(project = name)

            assert path is not None

            conn = sqlite3.connect(path + '/general_database.db', check_same_thread=False)
            cursor = conn.cursor()

            req = requests.get(paginas)
            web_s = req.content
            soup = BeautifulSoup(web_s, "html.parser")

            links = soup.find('frame', {'name': 'links'})
            src = links['src']
            
            req = requests.get(paginas + src)
            web_s = req.content
            soup_links = BeautifulSoup(web_s, "html.parser")
            
            menu = soup_links.find('ul', {'id': 'menu'})
            # Start the timer
            start_time = time.time()

            print("Project Started")
            parse_docentes(menu.findChildren(recursive=False)[0])
            parse_turmas(menu.findChildren(recursive=False)[1])
            parse_salas(menu.findChildren(recursive=False)[2])
            parse_ucs(menu.findChildren(recursive=False)[3])
            parse_turnos()
            fix_turmas_without_turnos()

            shutil.copy2(path + '/general_database.db', path + '/initial_database.db')

            proj.isParsed = True
            proj.save()
            print("Project Parsed")

            end_time = time.time()
            execution_time = end_time - start_time
            print("Execution Time:", execution_time, "seconds")
            conn.close()
            
        except Exception as e:
            print(traceback.format_exc())
            proj.delete()
            cursor.close()
            conn.close()
            
            try:
                shutil.rmtree("./database/Project"+str(projId))
            except:
                print(traceback.format_exc())
                print(f"Error deleting Project{projId} directory: {e}")
    try:
        executor.submit(run_parser)
        return JsonResponse({}, status=200)
    except Exception as e:
        return JsonResponse({"error": "Nao foi possivel fazer parse do site"}, status=400)
