from collections import defaultdict, deque
from ctypes import sizeof
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from bs4 import BeautifulSoup
import requests
import re
import sqlite3
from datetime import datetime, timedelta
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
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
import json


turnosMap = {}
max_workers = 4  # Estabelece o número máximo de threads permitidas
executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)

# Algumas tipologias encontradas
# 14 - O
# 15 - OT
# 16 - Pratica
# 17 - PL
# 18 - S
# 19 - Teorica
# 20 - TC
# 21 - Teorico-Pratica

# Não existe tipologia para além da 21, por isso consideram-se apenas tipologias entre td_tipologia_1 e td_tipologia_21
tipologias = ['td_tipologia_' + str(id) for id in range(1, 22)]

class Aula:
    """
    Classe auxiliar para encontrar aulas duplicadas
    """

    def __init__(self, dictionary):
        for key,value in dictionary.items():
            setattr(self, key, value)

    def __hash__(self):
        items = []
        for key, value in sorted(self.__dict__.items()):
            if isinstance(value, list):
                value = tuple(value)
            items.append((key, value))
        return hash(tuple(items))
    
    def __eq__(self, other):
        if isinstance(other, Aula):
            return self.__dict__ == other.__dict__
        return False

# -----------------------------------------------------------------------
# Funções auxiliares
# -----------------------------------------------------------------------

def table_to_matrix(table: any) -> list[list[any]]:
    """
    Transforma uma tabela HTML numa matriz.

    Recebe um elemento table HTML composto por elementos <td> e converte-o
    numa matriz, repetindo os elementos para que ocupem o mesmo número de
    linhas e colunas que os seus rowspans e colspans. Facilita o processo
    de mapear datas e durações de aulas.
    """

    # Encontra todas as linhas de uma tabela
    rows = table.find_all('tr')
    rows = rows[3:]
    
    # Determina o número de linhas e colunas na tabela
    num_rows = len(rows)
    num_cols = max([len(row.find_all(['td', 'th'])) for row in rows])
    
    # Cria uma matriz para armazenar os dados
    matrix = [[None for _ in range(num_cols)] for _ in range(num_rows)]
    # Itera sobre cada célula na tabela
    for i, row in enumerate(rows):
        cells = row.find_all('td')
        j = 0
        for cell in cells:
            # Encontra o rowspan e colspan da célula
            rowspan = int(cell.get('rowspan', 1))
            colspan = int(cell.get('colspan', 1))
            
            # Insere a data na matriz
            while matrix[i][j] is not None:
                j += 1
            for k in range(rowspan):
                for l in range(colspan):
                    matrix[i+k][j+l] = cell
            
            # Avança o índice da coluna para a próxima célula disponível
            j += colspan
    return matrix

def get_index(item: any, matrix: list[list[any]]) -> tuple[any, list[list[any]]]:
    """
    Encontra a coluna de um item numa matriz.

    Recebe um elemento <td> HTML e uma matriz. Procura pelo elemento na
    matriz, e guarda a sua coluna. A todas as posições da matriz é
    atribuído o valor None, e é devolvido um tuplo da coluna e a nova matriz.
    """

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
            
def get_dia_from_index(index: int, spanMap: dict[str, any]) -> str:
    """
    Recebe um índice e um mapa de spans HTML, devolvendo o dia da semana.
    """

    if index == 1:
        return 'Segunda'
    count = 0
    for (dia, span) in spanMap.items():
        count += int(span)
        if count >= index:
            return dia
        
def are_weeks_overlapped(si1: str, sf1:str, si2: str, sf2: str) -> bool:
    """
    Recebe dois intervalos de datas e determina se há sobreposição entre eles.
    """
    # Converte as strings para objetos datetime
    si1_obj = datetime.strptime(si1, "%Y-%m-%d")
    si2_obj = datetime.strptime(si2, "%Y-%m-%d")
    sf1_obj = datetime.strptime(sf1, "%Y-%m-%d")
    sf2_obj = datetime.strptime(sf2, "%Y-%m-%d")

    # Verifica se há overlap nos intervalos semanais
    overlap = si1_obj <= sf2_obj and sf1_obj >= si2_obj

    # Verifica se sf1 e si2 estão separados por uma semana ou menos
    one_week_or_less1 = abs(sf1_obj - si2_obj) <= timedelta(weeks=1)

    # Verifica se si1 e sf2 estão separados por uma semana ou menos
    one_week_or_less2 = abs(si1_obj - sf2_obj) <= timedelta(weeks=1)
    return overlap or one_week_or_less1 or one_week_or_less2

def min_date(date1: str, date2: str) -> str:
    """
    Recebe duas datas e devolve a que ocorre mais cedo.
    """
    date1_obj = datetime.strptime(date1, "%Y-%m-%d")
    date2_obj = datetime.strptime(date2, "%Y-%m-%d")
    early =  min(date1_obj, date2_obj)
    return datetime.strftime(early, "%Y-%m-%d")

def max_date(date1: str, date2: str) -> str:
    """
    Recebe duas datas e devolve a que ocorre mais tarde.
    """
    date1_obj = datetime.strptime(date1, "%Y-%m-%d")
    date2_obj = datetime.strptime(date2, "%Y-%m-%d")
    late = max(date1_obj, date2_obj)
    return datetime.strftime(late, "%Y-%m-%d")

# -----------------------------------------------------------------------
# Funções de interação com a base de dados
# -----------------------------------------------------------------------

def pre_inserir_blocos_vermelhos() -> None:
    """
    Preenche a tabela dos blocos vermelhos no arranque do parse.

    A tabela de blocos vermelhos, usada para consulta na base de dados, 
    é preenchida com todos os possíveis blocos de indisponibilidade que
    podem ser encontrados nos restantes horários.
    """

    # Verificar se a tabela já está preenchida
    stmt_count = '''SELECT COUNT(*) FROM blocosVermelhos'''
    cursor.execute(stmt_count)
    count = cursor.fetchone()[0]
    
    # Se a tabela estiver vazia, então preenche
    if count == 0:
        for dia in ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta','Sábado']:
            for hora in range(800, 2201, 100):  # Horários de 8h às 22h em intervalos de 100 minutos
                for minuto in [0, 30]:  # Minutos 0 e 30
                    horario = hora + minuto
                    stmt = '''INSERT INTO blocosVermelhos (hora, diaSemana) VALUES (?, ?)'''
                    cursor.execute(stmt, (horario, dia))
                    conn.commit()

def insert_cursos(cursos: list[tuple[str, str]], cursor: sqlite3.Cursor) -> None:
    """
    Recebe a lista dos cursos e insere-os na base de dados.
    """
    
    for (nome, abreviatura) in cursos:
        stmt = '''INSERT INTO curso(designacao, abreviacao) VALUES(?, ?)'''
        cursor.execute(stmt, (nome, abreviatura))
    return

def insert_ucs(ucs: dict[str, list[str, str, str]], id_curso: str, cursor: sqlite3.Cursor) -> None:
    """
    Recebe a lista das UCs e insere-as na base de dados
    """
    
    for sigla, (codigo, nome, numero) in ucs.items():
        stmt = '''INSERT OR IGNORE INTO uc (codigo, idCurso, nome, sigla, codOcorrencia) VALUES (?, ?, ?, ?, ?)'''
        cursor.execute(stmt, (codigo, id_curso, nome, sigla, numero))
    return

def insert_turma(id_curso: str, ano: str, codigo_turma: str, cursor: sqlite3.Cursor) -> None:
    """
    Recebe dados sobre uma turma e insere a informação na base de dados.
    """
    
    stmt = '''INSERT INTO turmas (idCurso, ano, codigo) VALUES (?, ?, ?)'''
    cursor.execute(stmt, (id_curso, ano, codigo_turma))
    return

def insert_aula(aula: Aula, cursor: sqlite3.Cursor) -> None:
    """
    Recebe um objeto Aula, extrai os seus dados e insere-os na base de dados.
    """
    
    isTeorica = aula.isTeorica
    duracao = aula.span
    salas = aula.salas
    turmas = aula.turmas
    docentes = aula.docentes
    hora = aula.hora
    dia = aula.dia
    semanaIni = aula.semanaIni
    semanaFin = aula.semanaFim
    codigo_uc = aula.cod_uc
        
    # Caso a aula não exista, são realizadas as inserções necessárias na DB
    stmtC = '''INSERT INTO aula (horaInicial, duracao, diaSemana, teorico, semanaInicial, semanaFinal) VALUES (?, ?, ?, ?, ?, ?)'''
    cursor.execute(stmtC, (hora, duracao, dia, isTeorica, semanaIni, semanaFin,))
    id_aula = cursor.lastrowid

    stmtAUC = '''INSERT OR IGNORE INTO aulaUC (idAula, idUC) VALUES (?, ?)'''
    cursor.execute(stmtAUC, (id_aula, codigo_uc,))
    
    for docente in docentes:
        stmtADC = '''INSERT OR IGNORE INTO aulaDocente (idAula, idDocente) VALUES (?, ?)'''
        cursor.execute(stmtADC, (id_aula, docente,))

    for turma in turmas: 
        stmtAT = '''INSERT OR IGNORE INTO aulaTurmas (idAula, idTurma) VALUES (?, ?)'''
        cursor.execute(stmtAT, (id_aula, turma,))

        stmtTUC = '''INSERT OR IGNORE INTO turmaUC (idTurma, idUC) VALUES (?, ?)'''
        cursor.execute(stmtTUC, (turma, codigo_uc,))
        
    for sala in salas.split(';'): 
        stmtAS = '''INSERT OR IGNORE INTO aulaSala (idAula, idSala) VALUES (?, ?)'''
        cursor.execute(stmtAS, (id_aula, sala,))
    return

# -----------------------------------------------------------------------
# Funções de parse
# -----------------------------------------------------------------------
        
def parse_horario_vermelhos(req: any, cursor: sqlite3.Cursor) -> list[int]: 
    """
    Recebe uma página e devole uma lista dos IDs de blocos vermelhos presentes.

    Realiza o parse dos blocos vermelhos num horário. O horário pode ser de
    turma, docente, sala ou UC. Devolve uma lista que contém os IDs de todos
    os blocos vermelhos encontrados, de acordo com a tabela de blocos vermelhos
    na base de dados.
    """

    soup = BeautifulSoup(req.content, "html.parser")

    # Obtém todos os elementos de bloco vermelho no horário
    vermelhos = soup.find_all('td', {'class':'td_vermelha'})
    
    # Se não existirem blocos vermelhos, devolve a lista vazia
    if len(vermelhos) == 0:
        return []
    
    redBlockList = []
    table = soup.find('center').find('table', {'class':'tabela_principal'})
    matrix = table_to_matrix(table)

    days = vermelhos[0].parent.parent.findChildren(recursive=False)[3]
    daySpans = {}
    
    for i, day in enumerate(days.findChildren()):
        if i == 0: continue
        daySpans[day.text] = day.get('colspan')

    # Para cada elemento de bloco vermelho
    for item in vermelhos:
        parent = item.parent
        index, matrix = get_index(item, matrix)

        # Obtém o dia e a hora
        time = int(parent.findChild().text.replace(':', ''))
        day = get_dia_from_index(index, daySpans)

        # Procura na BD o ID do bloco deste dia e hora
        stmt = '''SELECT id FROM blocosVermelhos WHERE hora=? AND diaSemana=?'''
        result = cursor.execute(stmt, (time, day)).fetchone()

        # Adiciona o ID do bloco à lista de blocos vermelhos
        redBlockList.append(result[0])
           
    return redBlockList

def parse_horario(req: requests.Response, curso_or_uc: str, parsingTurma: bool, lista_de_aulas: set[Aula]) -> None:
    """
    Realiza o parse do horário completo de uma página.

    Recebe uma página e realiza o parse do horário. A página pode ser de UC
    ou de turma (indicado pelo booleano parsingTurma). Todas as aulas
    encontradas são transformadas em objetos Aula e colocados num set, para
    garantir que não há ocorrências duplicadas.
    """

    soup = BeautifulSoup(req.content, "html.parser")
    
    # Obtenção de todos os blocos de aulas no horário
    aulaBlocks = soup.find('center').find_all('td', {'class':tipologias})

    # Parse de semana de início e fim deste horário
    semanas = soup.find('td', {'class':'cabtitulo'}).contents
    semanas = str(semanas[-1])
    semanaIniEFim = semanas.split("Semanas: ")[1]
    semanaIni, _, semanaFim = semanaIniEFim.partition(" - ")
    if not semanaFim:
        semanaFim = semanaIni

    si_obj = datetime.strptime(semanaIni, "%d/%m/%Y")
    sf_obj = datetime.strptime(semanaFim, "%d/%m/%Y")

    semanaIni = si_obj.strftime("%Y-%m-%d")
    semanaFim = sf_obj.strftime("%Y-%m-%d")

    # Parse de todas as UCs do horário (uma turma)
    if parsingTurma:
        ucs = parse_ucs(req)

        insert_ucs(ucs, curso_or_uc, cursor)
        conn.commit()

    # Parse e construção de uma tabela de docentes da turma
    docentes_table = soup.findAll('table')[3].findAll('tr')[2:]
    docentes_table = list(map(str, docentes_table))
    
    docentes_temp = defaultdict(list)

    for item in docentes_table:
        parts = item.split('<td align="left" valign="middle">')
        abrevs = parts[2].split('</td>')[0]
        codes = parts[3].split('</td>')[0]
        docentes_temp[abrevs].append(codes)

    # Parse das colunas dos dias de aulas
    dias = aulaBlocks[0].parent.parent.findChildren(recursive=False)[3]
    diaSpans = {}
    for i, dia in enumerate(dias.findChildren()):
        if i == 0: continue
        diaSpans[dia.text] = dia.get('colspan')

    # Criação de matriz a partir do horário
    table = soup.find('center').find('table', {'class': 'tabela_principal'})
    matrix = table_to_matrix(table)

    # Parse da informação nos blocos de aulas
    for aulaBlock in aulaBlocks:
        count = 0
        aula = {}
        aula['isTeorica'] = aulaBlock.get('class')[0] == 'td_tipologia_19'
        aula['span'] = aulaBlock.get('rowspan')
        pattern = r'\[(.*?)\]'
        matches = re.findall(pattern, aulaBlock.text)
        aula['salas'] = matches[2] if len(matches) > 2 else "Online"
        aula['turmas'] = matches[0].split('; ')

        docentes_aulaBlock = matches[1].replace('(', '').replace(')', '').split('; ')

        aula['semanaIni'] = semanaIni
        aula['semanaFim'] = semanaFim

        lista_docentes = []
        for i in docentes_aulaBlock:
            if (len(docentes_temp[i]) == 1):
                lista_docentes.append(docentes_temp[i][0])
            else:
                lista_docentes.append(docentes_temp[i][count])
                count += 1

        aula['docentes'] = lista_docentes

        # Adição de turnos da UC ao mapa de turnos global
        sigla = aulaBlock.contents[0]
        cod_uc = curso_or_uc if not parsingTurma else ucs[sigla][0]
        if (aula['isTeorica']):
            turnos = aula['turmas']
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

        # Parse de dia e hora da aulaBlock
        pai = aulaBlock.parent
        aula['hora'] = int(pai.findChild().text.replace(':', ''))
        index, matrix = get_index(aulaBlock, matrix)

        aula['dia'] = get_dia_from_index(index, diaSpans)
        aula['cod_uc'] = cod_uc
        
        # Inserir aulaBlock no set
        aula_obj = Aula(aula)
        lista_de_aulas.add(aula_obj)

    return

def parse_docentes(docentes: requests.Response) -> None:
    """
    Realiza o parse de todo o menu de docentes.

    Realiza o parse do menu de docentes, visitando cada uma das páginas
    individuais. Obtém os dados relevantes de cada docente, incluindo
    os seus blocos vermelhos.
    """

    children = docentes.find('ul').findChildren(recursive=False)
    for child in children:
        content = child.find('ul').find_all('li', recursive=False)
        k = 0
        for i in content:
            a = i.find('a', recursive=False)            
            link = a['href']
            req = requests.get(paginas+link)

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

            vermelhos = parse_horario_vermelhos(req, cursor)
            for idBlocoVermelho in vermelhos:
                stmtT = '''INSERT OR IGNORE INTO blocoDocente (idBloco, idDocente) VALUES (?, ?)'''
                cursor.execute(stmtT, (idBlocoVermelho, codigo))
                conn.commit()

        stmt = '''INSERT INTO docentes (numeroMecanografico, nome, abreviacao) VALUES (?, ?, ?)'''
        cursor.execute(stmt, (codigo, nome, sigla,))
        conn.commit()

    return

def parse_cursos(cursos: requests.Response) -> set[tuple[str, str]]:
    """
    Realiza o parse do menu de cursos.

    Realiza o parse do menu de cursos, obtendo a informação relevante. 
    Os tuplos (nome, abreviatura) são colocados num set para garantir que
    não há duplicados. Devolve o set de tuplos.
    """

    allCursos = set()

    for curso in cursos:
        info = curso.find('a').contents
        abreviatura = info[0].split(' - ')[0]
        nome = info[0].split(' - ', 1)[1]
        allCursos.add((nome, abreviatura))

    return allCursos

def parse_turmas(menu_turmas: any) -> None:
    """
    Realiza o parse do menu de turmas.

    Realiza o parse de todas as turmas, visitando cada horário individual.
    Obtém todas as aulas de cada horário, inserindo a informação relevante
    na base de dados.
    """

    children = menu_turmas.find('ul').findChildren(recursive=False)
    
    # Parse de cursos a partir do menu lateral
    cursos = parse_cursos(children)
    # Inserir cursos na DB
    insert_cursos(cursos, cursor)
    
    for child in children:
        idCurso = child.find('a').contents
        idCurso = idCurso[0].split(" - ")[0]
        anos = child.find('ul').findChildren(recursive=False)

        for ano in anos:
            numeroAno = ano.find('a').contents
            numeroStr = numeroAno[0]
            numeroStr = numeroStr.split(" ")[1]
            plano_turmas = ano.find('ul').find('li')
            turmas = plano_turmas.find('ul').findChildren(recursive=False)

            lista_de_aulas = set()

            for turma in turmas:
                codigo = turma.find('a').contents
                codigo = str(codigo).split("'")[1]
                semanasLi = turma.find('ul').find_all('li')

                # Inserir turma na BD
                insert_turma(idCurso, numeroStr, codigo, cursor)
                conn.commit()

                parsed_vermelhos = False

                for semana in semanasLi:
                    a = semana.find('a', recursive=False)
                
                    # Link para horário da semana
                    link = a['href']
                    req = requests.get(paginas + link)

                    parse_horario(req, idCurso, True, lista_de_aulas)

                    # Os blocos vermelhos de uma turma só precisam de ser 
                    # parsed uma vez, já que não mudam entre semanas
                    if not parsed_vermelhos:
                        vermelhos = parse_horario_vermelhos(req, cursor)
                        for idBlocoVermelho in vermelhos:
                            stmt = '''INSERT OR IGNORE INTO blocoTurma (idBloco, idTurma) VALUES (?, ?)'''
                            cursor.execute(stmt, (idBlocoVermelho, codigo))
                            conn.commit()
                        parsed_vermelhos = True

            for aula in lista_de_aulas:
                insert_aula(aula, cursor)
            
            lista_de_aulas = set()

    conn.commit()

def parse_ucs(req: requests.Response) -> dict[str, list[str, str, str]]:
    """
    Realiza o parse de UCs na página de cada turma.

    Recebe uma página de horário de uma turma e realiza o parse de todas
    as UCs presentes. Devolve um dicionário com entradas indexadas pela
    sigla da UC.
    """

    soup = BeautifulSoup(req.content, "html.parser")

    table = [str(row) for row in soup.findAll('table')[4].findAll('tr')[2:]]
    
    ucs = {}
    for row in table:
        row_items = row.split('<td align="left" valign="middle">')[1:]
        (codigo_nome, sigla, numero_uc) = map(lambda item: item.split('</td>')[0], row_items)
        (codigo, nome) = codigo_nome.split(" - ", 1)

        ucs[sigla] = [codigo, nome, numero_uc]
    return ucs

def parse_salas(salas: any) -> None:
    """
    Realiza o parse das salas a partir do menu lateral.

    Recebe o elemento do menu correspondente às salas e realiza o parse de
    cada uma, guardando os elementos relevantes, incluindo os blocos
    vermelhos. 
    """

    children = salas.find('ul').findChildren(recursive=False)
    for child in children:
        a_list = child.find_all('a', {'class':"timetable-link"})
        content = child.find('a').contents
        if ("__cf_email__" in str(content)):
            content = ['EaD']
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
            link = a.get('href')
            req = requests.get(paginas+link)
            vermelhos = parse_horario_vermelhos(req, cursor)
            for idBlocoVermelho in vermelhos:
                stmtT = '''INSERT OR IGNORE INTO salaBloco (idBloco, idSala) VALUES (?, ?)'''
                cursor.execute(stmtT, (idBlocoVermelho, sala))
                conn.commit()   
    return

def parse_turnos() -> None:
    """
    Insere os turnos encontrados na base de dados.

    Usa a informação na estrutua global turnosMap para preencher a tabela
    correspondente aos turnos na base de dados.
    """

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

def fix_turmas_without_turnos() -> None:
    """
    Atribui um turno às turmas que não têm um turno associado na base de dados.

    """

    # Obtém a lista de turmas em turmaUC que não existem na tabela turnos
    query = '''
        SELECT tu.idTurma, tu.idUC
        FROM turmaUC tu
        LEFT JOIN turno tn ON tu.idTurma = tn.idTurma
        WHERE tn.idTurma IS NULL
    '''
    cursor.execute(query)
    missing_turmas = cursor.fetchall()

    # Cria entradas em turnos para cada turma em falta
    for turma in missing_turmas:
        idTurma, idUC = turma
        query = '''
            INSERT INTO turno (numero, idTurma, idUC)
            VALUES (0, ?, ?)
        '''
        cursor.execute(query, (idTurma, idUC))        
    conn.commit()

def aulas_simultaneas():
    """
    Encontra aulas simultâneas no horário e insere a informação na base de dados.

    Realiza uma query à base de dados para encontrar aulas simultâneas de 
    cursos diferentes. Aulas simultâneas têm os mesmos: docente, sala, dia, e
    hora. Há também uma sobreposição nas semanas em que ocorrem. No entanto,
    o curso e a UC têm de ser diferentes. Depois de encontradas as aulas, são
    inseridas numa tabela apropriada na base de dados.
    """

    query = '''
        SELECT DISTINCT
            CASE WHEN a1.id < a2.id THEN a1.id ELSE a2.id END AS id_aula1,
            CASE WHEN a1.id < a2.id THEN a2.id ELSE a1.id END AS id_aula2,
            uc1.idCurso AS id_curso1,
            uc2.idCurso AS id_curso2
        FROM aula AS a1
        JOIN aulaSala AS asala1 ON a1.id = asala1.idAula
        JOIN aulaDocente AS ad1 ON a1.id = ad1.idAula
        JOIN aulaUC AS auc1 ON a1.id = auc1.idAula
        JOIN uc AS uc1 ON auc1.idUC = uc1.codigo
        JOIN aula AS a2
        JOIN aulaSala AS asala2 ON a2.id = asala2.idAula
        JOIN aulaDocente AS ad2 ON a2.id = ad2.idAula
        JOIN aulaUC AS auc2 ON a2.id = auc2.idAula
        JOIN uc AS uc2 ON auc2.idUC = uc2.codigo
        WHERE a2.id > a1.id
            AND ad1.idDocente = ad2.idDocente
            AND asala1.idSala = asala2.idSala
            AND a1.diaSemana = a2.diaSemana
            AND a1.horaInicial = a2.horaInicial
            AND (
                (a1.semanaInicial <= a2.semanaFinal AND a1.semanaFinal >= a2.semanaInicial)
                OR
                (a1.semanaInicial >= a2.semanaInicial AND a1.semanaFinal <= a2.semanaFinal)
                OR
                (a1.semanaInicial <= a2.semanaInicial AND a1.semanaFinal >= a2.semanaFinal)
            )
            AND uc1.idCurso <> uc2.idCurso;
    '''
    cursor.execute(query)
    aulas_sim = cursor.fetchall()

    for entry in aulas_sim:
        idAula1, idAula2, idCurso1, idCurso2 = entry
        query = '''
            INSERT into aulasSimultaneas (aula1, aula2, curso1, curso2)
            VALUES (?, ?, ?, ?)
        '''
        cursor.execute(query, (idAula1, idAula2, idCurso1, idCurso2))
    
    conn.commit()

def selecionar_aulas_em_paralelo(request):
    project_id = request.GET.get("id")

    db_path = os.path.join(settings.BASE_DIR, "database", f"Project{project_id}", "initial_database.db")
    db_path = os.path.join(settings.BASE_DIR, "database", f"Project{project_id}", "initial_database.db")

    conn = sqlite3.connect(db_path) 
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            a.id AS aula_id,
            at.idTurma AS turma_id,
            a.diaSemana,
            a.horaInicial,
            a.semanaInicial,
            auc.idUC,
            uc.idCurso,
            uc.nome AS nomeUC
        FROM aula a
        JOIN aulaTurmas at ON a.id = at.idAula
        JOIN aulaUC auc ON a.id = auc.idAula
        JOIN uc ON auc.idUC = uc.codigo
        WHERE a.teorico = FALSE
    ''')

    resultados_query = cursor.fetchall()

    # Agrupar numa lista aulas da mesma UC  (e curso) que são ao mesmo tempo
    grupos_dict = defaultdict(list)
    for row in resultados_query:
        key = (
            row['diaSemana'],
            row['horaInicial'],
            row['semanaInicial'],
            row['idUC'],
            row['nomeUC'],
            row['idCurso']
        )
        turmas_por_aula = grupos_dict.setdefault(key, defaultdict(set))
        turmas_por_aula[row['aula_id']].add(row['turma_id'])

    grupos_list = []
    for i, (key, aulas) in enumerate(grupos_dict.items(), start=1):
        if len(aulas) <= 1:
            continue

        dia_semana, hora_inicial, semana_inicial, codigoUC, nomeUC, id_curso = key
        hora_str = f"{hora_inicial:04d}"
        hora_str = f"{hora_str[:2]}:{hora_str[2:]}"
        horario_str = f"{dia_semana}, {hora_str}"

        num_boxes = len(aulas) // 2

        grupo_dict = {
            'id': i,
            'uc': codigoUC,
            'nomeUC': nomeUC,
            'curso': id_curso,
            'horario': horario_str,
            'aulas': sorted([
                (aula_id, sorted([turma.strip() for turma in turmas]))
                for aula_id, turmas in aulas.items()
            ], key=lambda x: x[1][0]),
            'num_boxes': num_boxes
        }

        grupos_list.append(grupo_dict)

    cursos_unicos = sorted(set(grupo['curso'] for grupo in grupos_list))

    grupos_list.sort(key=lambda g: (g["curso"], g["nomeUC"]))

    aulas_em_paralelo = obter_aulas_em_paralelo(project_id)
    
    conn.close()

    return render(request, 'selecionar_aulas_em_paralelo.html', {
        'grupos_aulas_ao_mesmo_tempo': grupos_list,
        'cursos': cursos_unicos,
        'project_id': project_id,
        'aulas_em_paralelo' : aulas_em_paralelo,
    })

def obter_aulas_em_paralelo(projId):
    """
    Recebe um cursor de SQLite já conectado à base de dados de um projeto.
    Devolve as aulas que atualmente estão guardadas como aulas em paralelo, em forma
    de uma lista dos grupos de aulas em paralelo (que são listas de IDs de aulas).
    """

    db_path = os.path.join(settings.BASE_DIR, "database", f"Project{projId}", "general_database.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute('SELECT aula1, aula2 FROM turmasSimultaneas')
    pares = cursor.fetchall()

    # Construir grafo aula -> vizinhos
    adj = defaultdict(set)
    for a1, a2 in pares:
        adj[a1].add(a2)
        adj[a2].add(a1)

    # Obter cadeias
    visitados = set()
    cadeias = []

    for aula in adj:
        if aula in visitados:
            continue

        fila = deque([aula])
        cadeia = []

        while fila:
            atual = fila.popleft()
            if atual in visitados:
                continue
            visitados.add(atual)
            cadeia.append(atual)
            fila.extend(adj[atual] - visitados)

        cadeia.sort()
        cadeias.append(cadeia)

    return cadeias

@csrf_exempt
def guardar_aulas_em_paralelo(request):
    try:
        data = json.loads(request.body)
        pares = data["pares"]  # [(aula1, aula2, turma1, turma2), ...]

        if len(pares) == 0:
            return JsonResponse({'status': 'ignorado'})

        project_id = request.GET.get("id")
        db_path = os.path.join(settings.BASE_DIR, "database", f"Project{project_id}", "general_database.db")

        with sqlite3.connect(db_path, timeout=10) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM turmasSimultaneas')
            for a1, a2, t1, t2 in pares:
                cursor.execute('''
                    INSERT INTO turmasSimultaneas (aula1, aula2, turma1, turma2)
                    VALUES (?, ?, ?, ?)
                ''', (a1, a2, t1, t2))
            conn.commit()

        inconsistentes = verificar_aulas_em_paralelo(request, project_id, pares)

        project = Project.objects.get(id=project_id)
        project.has_selected_aulas_em_paralelo = True
        project.save()

        return JsonResponse({
            'status': 'ok',
            'inconsistentes': inconsistentes
        })
        return JsonResponse({
            'status': 'ok',
            'inconsistentes': inconsistentes
        })

    except Exception as e:
        return JsonResponse({'status': 'erro', 'message': str(e)}, status=500)

def verificar_aulas_em_paralelo(request, projId, pares):
    """
    Função destinada para casos em que o utilizador muda os grupos de aulas em paralelo depois de já terem sido realizado trocas.
    Esta função verifica quais dos grupos da nova seleção de aulas em paralelo sofreram mudanças e não estão, de momento, a ser dadas ao mesmo
    tempo deviso às trocas.
    """    
    # 1. Construir grafo aula -> vizinhos
    adj = defaultdict(set)
    for a1, a2, _, _ in pares:
        adj[a1].add(a2)
        adj[a2].add(a1)

    # 2. Obter grupos de aulas simultâneas em forma de cadeia
    visitados = set()
    cadeias = []

    for aula in adj:
        if aula in visitados:
            continue

        fila = deque([aula])
        cadeia = []

        while fila:
            atual = fila.popleft()
            if atual in visitados:
                continue
            visitados.add(atual)
            cadeia.append(atual)
            fila.extend(adj[atual] - visitados)

        cadeia.sort()
        cadeias.append(cadeia)

    # 3. Verificar para cada cadeia se as aulas têm o mesmo dia, hora e intervalo de semanas
    inconsistentes = []

    db_path = os.path.join(settings.BASE_DIR, "database", f"Project{projId}", "general_database.db")

    conn = sqlite3.connect(db_path) 
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    for cadeia in cadeias:
        cursor.execute(
            f'''
            SELECT id, diaSemana, horaInicial, semanaInicial, semanaFinal
            FROM aula
            WHERE id IN ({','.join(['?'] * len(cadeia))})
            ''', cadeia
        )
        aulas_info = cursor.fetchall()

        # Normalizar comparação
        referencia = (
            aulas_info[0]["diaSemana"],
            aulas_info[0]["horaInicial"],
            aulas_info[0]["semanaInicial"],
            aulas_info[0]["semanaFinal"],
        )

        for aula in aulas_info[1:]:
            atual = (aula["diaSemana"], aula["horaInicial"], aula["semanaInicial"], aula["semanaFinal"])
            if atual != referencia:
                inconsistentes.append(cadeia)
                break  # esta cadeia já está marcada como inconsistente

    if inconsistentes:
        grupos_inconsistentes = []

        for cadeia in inconsistentes:
            cursor.execute(
                f'''
                SELECT a.id, uc.nome as nomeUC, group_concat(t.codigo, ', ') as turmas
                FROM aula a
                JOIN aulaUC auc ON a.id = auc.idAula
                JOIN uc ON auc.idUC = uc.codigo
                JOIN aulaTurmas at ON a.id = at.idAula
                JOIN turmas t ON at.idTurma = t.codigo
                WHERE a.id IN ({','.join(['?'] * len(cadeia))})
                GROUP BY a.id
                ''', cadeia
            )
            aulas = cursor.fetchall()
            if aulas:
                nome_uc = aulas[0]["nomeUC"]
                lista = {
                    "nome_uc": nome_uc,
                    "aulas": [f"Aula com as turmas: {a['turmas']}" for a in aulas]
                }
                grupos_inconsistentes.append(lista)
        
        conn.close()
        return grupos_inconsistentes
    conn.close()

def verificar_aulas_em_paralelo(request, projId, pares):
    """
    Função destinada para casos em que o utilizador muda os grupos de aulas em paralelo depois de já terem sido realizado trocas.
    Esta função verifica quais dos grupos da nova seleção de aulas em paralelo sofreram mudanças e não estão, de momento, a ser dadas ao mesmo
    tempo deviso às trocas.
    """    
    # 1. Construir grafo aula -> vizinhos
    adj = defaultdict(set)
    for a1, a2, _, _ in pares:
        adj[a1].add(a2)
        adj[a2].add(a1)

    # 2. Obter grupos de aulas simultâneas em forma de cadeia
    visitados = set()
    cadeias = []

    for aula in adj:
        if aula in visitados:
            continue

        fila = deque([aula])
        cadeia = []

        while fila:
            atual = fila.popleft()
            if atual in visitados:
                continue
            visitados.add(atual)
            cadeia.append(atual)
            fila.extend(adj[atual] - visitados)

        cadeia.sort()
        cadeias.append(cadeia)

    # 3. Verificar para cada cadeia se as aulas têm o mesmo dia, hora e intervalo de semanas
    inconsistentes = []

    db_path = os.path.join(settings.BASE_DIR, "database", f"Project{projId}", "general_database.db")

    conn = sqlite3.connect(db_path) 
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    for cadeia in cadeias:
        cursor.execute(
            f'''
            SELECT id, diaSemana, horaInicial, semanaInicial, semanaFinal
            FROM aula
            WHERE id IN ({','.join(['?'] * len(cadeia))})
            ''', cadeia
        )
        aulas_info = cursor.fetchall()

        # Normalizar comparação
        referencia = (
            aulas_info[0]["diaSemana"],
            aulas_info[0]["horaInicial"],
            aulas_info[0]["semanaInicial"],
            aulas_info[0]["semanaFinal"],
        )

        for aula in aulas_info[1:]:
            atual = (aula["diaSemana"], aula["horaInicial"], aula["semanaInicial"], aula["semanaFinal"])
            if atual != referencia:
                inconsistentes.append(cadeia)
                break  # esta cadeia já está marcada como inconsistente

    if inconsistentes:
        grupos_inconsistentes = []

        for cadeia in inconsistentes:
            cursor.execute(
                f'''
                SELECT a.id, uc.nome as nomeUC, group_concat(t.codigo, ', ') as turmas
                FROM aula a
                JOIN aulaUC auc ON a.id = auc.idAula
                JOIN uc ON auc.idUC = uc.codigo
                JOIN aulaTurmas at ON a.id = at.idAula
                JOIN turmas t ON at.idTurma = t.codigo
                WHERE a.id IN ({','.join(['?'] * len(cadeia))})
                GROUP BY a.id
                ''', cadeia
            )
            aulas = cursor.fetchall()
            if aulas:
                nome_uc = aulas[0]["nomeUC"]
                lista = {
                    "nome_uc": nome_uc,
                    "aulas": [f"Aula com as turmas: {a['turmas']}" for a in aulas]
                }
                grupos_inconsistentes.append(lista)
        
        conn.close()
        return grupos_inconsistentes
    conn.close()



# -----------------------------------------------------------------------
# Função parse()
# -----------------------------------------------------------------------

def parse(request: requests.Request) -> JsonResponse:    
    """
    Inicia o parse de um novo projeto.

    Prepara as variáveis e realiza as verificações necessárias para realizar
    o parse da página de horários. Chama a função run_parser numa nova thread,
    enquanto houver threads disponíveis.
    """

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
    
    def run_parser():
        """
        Função executora do parse.

        Função de parse que corre em cada thread, chamada por parse().
        Obtém o URL da página a realizar o parse e o nome do projeto a partir
        do POST request. Cria a entrada do projeto na base de dados, o
        a diretoria do projeto, e a ligação à base de dados. Chama as outras
        funções de parse para preencher a base de dados. No final, copia o
        conteúdo da general_database criada para a initial_database, e marca
        o projeto como parsed. Em caso de falha do parse, a base de dados é
        eliminada e a diretoria é eliminada.
        """
        
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
            
            print("Project Started")
            pre_inserir_blocos_vermelhos()
            
            parse_docentes(menu.findChildren(recursive=False)[0])

            parse_turmas(menu.findChildren(recursive=False)[1])
            
            parse_salas(menu.findChildren(recursive=False)[2])

            parse_turnos()

            fix_turmas_without_turnos()

            cleanup_aulas()

            aulas_simultaneas()

            shutil.copy2(path + '/general_database.db', path + '/initial_database.db')

            proj.isParsed = True
            proj.save()
            print("Project Parsed")

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
    
def cleanup_aulas() -> None:
    # Get all unique aulas
    stmtAulas = '''SELECT DISTINCT diaSemana, horaInicial, duracao, teorico, idDocente, idUC, idTurma
                    FROM aula 
                    JOIN aulaDocente ON aula.id = aulaDocente.idAula
                    JOIN aulaUC ON aula.id = aulaUC.idAula
                    JOIN aulaTurmas ON aula.id = aulaTurmas.idAula'''
    cursor.execute(stmtAulas)
    aulas = cursor.fetchall()

    for aula in aulas:
        dia, hora, duracao, isTeorica, docente, uc, turma = aula
        # Get all entries for this aula
        stmtTest = '''SELECT * FROM aula 
                      JOIN aulaDocente ON aula.id = aulaDocente.idAula
                      JOIN aulaUC ON aula.id = aulaUC.idAula
                      JOIN aulaTurmas ON aula.id = aulaTurmas.idAula
                      WHERE diaSemana=? AND horaInicial=? AND duracao=? AND teorico=? AND idDocente=? AND idUC=? AND idTurma=?'''
        cursor.execute(stmtTest, (dia, hora, duracao, isTeorica, docente, uc, turma))
        results = cursor.fetchall()

        # Merge all overlapping entries
        while len(results) > 1 and any(are_weeks_overlapped(results[i][5], results[i][6], results[j][5], results[j][6]) for i in range(len(results)) for j in range(i+1, len(results))):
            # Sort results by semanaInicial
            results.sort(key=lambda x: x[5])
            # Check if the first two entries overlap
            idAula1, si1, sf1 = results[0][0], results[0][5], results[0][6]
            idAula2, si2, sf2 = results[1][0], results[1][5], results[1][6]
            if are_weeks_overlapped(si1, sf1, si2, sf2):
                # Merge the two entries
                ssi = min_date(si1, si2)
                ssf = max_date(sf1, sf2)
                # Update the new dates in the results array
                results_list = list(results[0])

                results_list[5] = ssi
                results_list[6] = ssf

                results[0] = tuple(results_list)
                stmtUpdate = '''UPDATE aula SET semanaInicial=?, semanaFinal=?
                                WHERE id=?'''
                cursor.execute(stmtUpdate, (ssi, ssf, idAula1))
                # Update references in tables referencing aula
                tables = ['aulaDocente', 'aulaUC', 'aulaSala', 'aulaTurmas']
                for table in tables:
                    stmtDeleteRef = f'''DELETE FROM {table}
                                        WHERE idAula=?'''
                    cursor.execute(stmtDeleteRef, (idAula2,))
                # Delete the second entry
                stmtDelete = '''DELETE FROM aula WHERE id=?'''
                cursor.execute(stmtDelete, (idAula2,))
                
                # Remove the entry of aula2 from the results
                results.pop(1)
                continue
            # Remove the first entry from the results
            results.pop(0)
    conn.commit()