import logging
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpRequest, JsonResponse
from django.template.loader import render_to_string
from .models import Curso, Ano, Docente, UC, Aula, Sala, Bloco, AulaInfo, AulaChange
import sqlite3
import os
import shutil
import src.getHorariosFromDB.filteredScheduleFunctions as func
import src.getHorariosFromDB.auxiliaryScheduleFunctions as auxfunc
import json
import bleach
import re
from datetime import datetime
from src.users.models import User
from src.projects.models import Group, Project
from django.contrib import messages
from src.getHorariosFromDB.movementFunctions import addDocente, removeDocente, addSala, removeSala, moveAula, changeUC, updateAulaDuration, addTurma, removeTurma
from src.getHorariosFromDB.conflictFunctions import organizeInformation, findAnyConflicts
from src.getHorariosFromDB.comparingDatabases import getDifferencesFromDatabases
from src.getHorariosFromDB.utils import organize_changes, append_aula_data
from src.getHorariosFromDB.models import Node, GraphManager, Graph, Edge, Conflict_Manager
import src.getHorariosFromDB.graph as graph_controller
from src.FeupScheduleEditor.utils import reverse_time_span_conversion, switch_number_to_day

# Configure basic logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # Logs to console
    ]
)

# Get a logger for this module
logger = logging.getLogger(__name__)


PLACEHOLDER_ID = 0
dias = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]
horas = ["8:00", "8:30", "9:00", "9:30", "10:00", "10:30", "11:00", "11:30", "12:00", "12:30", "13:00", "13:30", "14:00", "14:30", "15:00", "15:30", "16:00", "16:30", "17:00", "17:30", "18:00", "18:30", "19:00", "19:30"]

validator = True


class CursoEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Curso):
            return {
                'nome': obj.nome,
                'anos': self.process_obj(obj.anos),
                'docentes': self.process_obj(obj.docentes),
                'ucs': self.process_obj(obj.ucs),
                'salas': self.process_obj(obj.salas)
            }
        elif isinstance(obj, Docente):
            return {
                'numMecanografico': obj.numMecanografico,
                'nome': obj.nome,
                'abreviacao': obj.abreviacao,
                'aulas': obj.aulas,
                'blocos': obj.blocos,
                'miniHorario': obj.miniHorario
            }
        elif isinstance(obj, Aula):
            return {
                'id': obj.id,
                'horaInicial': obj.horaInicial,
                'duracao': obj.duracao,
                'diaSemana': obj.diaSemana,
                'isTeorica': obj.isTeorica,
                'turmas' : obj.turmas,
                'semanaInicial': obj.semanaInicial,
                'semanaFinal': obj.semanaFinal,
            }
        elif isinstance(obj, UC):
            return {
                'codigo': obj.codigo,
                'nome': obj.nome,
                'sigla': obj.sigla,
                'aulas': obj.aulas,
                'anos': obj.anos,
            }
        elif isinstance(obj, Ano):
            return {
                'ano': obj.ano,
                'numTurmas': obj.numTurmas,
                'turmasPorTurno': obj.turmasPorTurno,
                'turmas': obj.turmas,
                'docentes': obj.docentes,
                'semanas': obj.semanas,
            }
        elif isinstance(obj, Sala):
            return {
                'numero': obj.numero,
                'tipo': obj.tipo,
                'capacidade': obj.capacidade,
                'aulas': obj.aulas,
                'blocos': obj.blocos,
                'miniHorario': obj.miniHorario
            }
        elif isinstance(obj, Bloco):
            return {
                'id': obj.id,
                'hora': obj.hora,
                'diaSemana': obj.diaSemana,
            }
            
        return super().default(obj)
    
    def process_obj(self, objs):
        result = []
        for obj in objs:
            result.append(self.default(obj))
        return result

# getProjetosListAux
#
# Auxiliary function that retrieves the list of projects that the user can see
# Used in the starter page project cards and in the header, in most pages
def getProjetosListAux(request, userId):
    projects = Project.objects.values_list("creator", "group", "people", "pk", "name", "finished_ingestion_at")
    related = []

    courses = User.objects.values("member_groups").filter(pk=userId)

    merge_courses = []

    for i in courses:
        if not i["member_groups"] in merge_courses:
            merge_courses.append(i["member_groups"])

    person = userId
    ids = []
    for project in projects:
        if project[3] in ids:
            continue
        elif person == project[0] or person == project[2] or (project[1] in merge_courses and project[1] != None and merge_courses != None) or request.user.is_staff:
            ids.append(project[3])
            related.append({'id':project[3], 'nome': project[4], 'finished_ingestion_at':project[5]})
    related.reverse()
    return related

def areSemanasCompatible(siAula, sfAula, siSelected, sfSelected):
    return (siAula == siSelected and sfAula == sfSelected) or (siAula < siSelected and sfAula == sfSelected) or (siAula == siSelected and sfAula > sfSelected)
# ---------------------------------------------------------------------------------------------------------

def starter(request: HttpRequest) -> HttpResponse:
    '''
    Obtém a lista de projetos atuais e cria a página `starter`
    
    Parameters:
    request (HttpRequest): O objeto HTTP request
        
    Returns:
    HttpResponse: O objeto HTTP response, correspondente à página `starter`
    '''

    # Se o utlizador não estiver autenticado, redireciona para a página de login
    if (not request.user.is_authenticated):
        return redirect('login/')
    
    projetos = getProjetosListAux(request, request.user.pk)

    return render(request, 'starter/starter.html', {'projetos' : projetos, 'is_edit_turnos': False})

def manageProjects(request: HttpRequest, projId: int) -> HttpResponse:
    '''
    Cria a página `manageProjects` para gestão de pessoas e grupos associados a projetos.

    Parameters:
    request (HttpRequest): O objeto HTTP request.
    projId (int): O ID do projeto.

    Returns:
    HttpResponse: O objeto HTTP response, correspondente à página `manageProjects`.
    '''
    
    # Se o utlizador não estiver autenticado, redireciona para a página de login
    if (not request.user.is_authenticated):
        return redirect('login/')

    if request.method == 'POST':
        a = request.POST
        project = Project.objects.get(pk = projId)
        for i in a.getlist('Join'):
            project.group.add(Group.objects.get(name = i))
        for i in a.getlist('Remove'):
            project.group.remove(Group.objects.get(name = i))            
        for i in a.getlist('JoinP'):
            project.people.add(User.objects.get(username=i))
        for i in a.getlist('RemoveP'):
            project.people.remove(User.objects.get(username=i))

    courses = User.objects.filter(pk=request.user.pk).values("member_groups")

    projCourses = Project.objects.values("group").filter(pk = projId)

    temp = []
    for x in courses:
        check = True
        for i in projCourses:
            if x['member_groups'] == i['group']:
                check = False
        if check:
            temp.append(x)

    courses = temp

    group = []

    temp = []
    if (courses):
        for i in courses:
            temp.append(Group.objects.values_list("name", "abreviation").get(pk = i["member_groups"]))

    group.append(temp)

    temp = []

    for i in projCourses:
        if i["group"] != None:
            temp.append(Group.objects.values_list("name", "abreviation").get(pk = i["group"]))

    group.append(temp)

    people = User.objects.all().values("pk")

    peopleProj = Project.objects.filter(pk = projId).values("people")
    
    temp = []
    for x in people:
        check = True
        for i in peopleProj:
            if x['pk'] == i['people']:
                check = False
        if check:
            temp.append(x)

    people = temp

    humans = []

    temp = []
    if (people):
        for i in people:
            temp.append(User.objects.get(pk=i['pk']))

    humans.append(temp)

    temp = []
    for i in peopleProj:
        if i["people"] != None:
            temp.append(User.objects.get(pk=i['people']))

    humans.append(temp)

    return render(request, 'starter/manageProj.html', {'groups':group, 'people': humans})


def groups(request):    
    if (not request.user.is_authenticated):
        return redirect('login/')

    group = Group.objects.values_list("name", "pk", "abreviation")
    groups = []
    people = User.objects.values_list("pk", "member_groups")
    user_groups = []
    user_in_group = []
    user_not_in_group = []

    if request.method == 'POST':
        a = request.POST
        if "Create" in a:
            name = a.get('name')
            # add first letter
            oupt = name[0]
            # iterate over string
            for i in range(1, len(name)):
                if name[i-1] == ' ':
                    # add letter next to space
                    oupt += name[i]  
            # uppercase oupt
            oupt = oupt.upper()


            courses = Group.objects.values_list("abreviation", "name")
            check = True
            for i in courses:
                #print(i)
                if name == i[1] or oupt == i[0]:
                    check = False
                    break

            if check:
                b = Group(name = name, abreviation = oupt)
                b.save()
                b.members.add(request.user)
                messages.info(request, "Grupo criado")

        elif "Out" in a:
            pk = request.user.pk
            if Group.objects.filter(abreviation = a.get('Out')).exists():
                group_id = Group.objects.get(abreviation = a.get('Out'))
                group_id.members.remove(request.user)

                check = True
                for k in people:
                    if k[0] != request.user.pk and k[1] == group_id.pk:
                        check = False
                
                if check:
                    Group.objects.get(abreviation = a.get('Out')).delete()
                

        else:
            group_id = Group.objects.get(abreviation = a.get('Group'))
            for i in a.getlist('Join'):
                group_id.members.add(User.objects.get(username=i))
            for i in a.getlist('Remove'):
                group_id.members.remove(User.objects.get(username=i))

    for i in people:
        if i[0] == request.user.pk:
            user_groups.append(i[1])
            for a in group:
                if a[1] == i[1]:
                    groups.append([a[0],a[2]])
            temp = []
            temp1 = []
            for k in people:
                if k[0] != request.user.pk:
                    if k[1] == i[1] or request.user.is_staff:
                        if User.objects.get(pk=k[0]) in temp1:
                            temp1.remove(User.objects.get(pk=k[0]))
                        temp.append(User.objects.get(pk=k[0]))
                    else:
                        if not (User.objects.get(pk=k[0]) in temp1 or User.objects.get(pk=k[0]) in temp):
                            temp1.append(User.objects.get(pk=k[0]))
            user_in_group.append(temp)
            user_not_in_group.append(temp1)


    final = []

    for i in range(len(groups)):
        temp = {}
        temp[0] = groups[i]
        temp[1] = user_not_in_group[i]
        temp[2] = user_in_group[i]
        final.append(temp)

    return render(request, 'starter/joinGroup.html', {'groups':final})


# deleteProject
#
# Post Ajax request handler function
# Checks if the project can be deleted and, if so, deletes the database entry and 
# the corresponding project directory
def deleteProject(request):
    if (not request.user.is_authenticated):
        return JsonResponse({"error": "User is not authenticated", "id": projId}, status=401)
    if request.method != "POST" and not request.is_ajax():
        return JsonResponse({"error": "Invalid request", "id": projId}, status=400)    

    try:
        projId = request.POST.get("id")

        proj = Project.objects.get(pk = projId)
        proj.delete()

        shutil.rmtree("./database/Project"+projId)
        return JsonResponse({"id": projId}, status=200)
    except AssertionError as e:
        return JsonResponse({"error": "Could not delete project, exception: \"{}\"".format(e), "id": projId}, status=401)
    except Exception as e:
        return JsonResponse({"error": "Could not delete project, exception: \"{}\"".format(e), "id": projId}, status=400)


def editTurnos(request: HttpRequest, projId: int) -> HttpResponse:
    """
    Cria a página `editTurnos` para o projeto selecionado.

    Primeiro verifica se é a primeira vez que a página é aberta para saber se é para
    redirecionar para a página da seleção de aulas em paralelo. Caso a seleção das
    aulas em paralelo já esteja feita então procede ao carregamento da página `editTurnos`.
    redirecionar para a página da seleção de aulas em paralelo. Caso a seleção das
    aulas em paralelo já esteja feita então procede ao carregamento da página `editTurnos`.

    Começa por obter a informação do projeto e o json dos cursos, assim como
    os conflitos existentes até à altura. Usa essa informação para 
    fazer o render da página.

    Parameters:
    request (HttpRequest): O objeto Http request.
    projId (int): O ID do projeto.

    Returns:
    HttpResponse: O objeto Http response que contém a página `editTurnos` criada.
    """
    if (not request.user.is_authenticated):
        return redirect('login/')
    #projetos = Project.objects.filter(person = Person.objects.get(username = request.user.pk))
    projetos = getProjetosListAux(request, request.user.pk)
    projeto = Project.objects.values_list().get(id = projId)

    # verificar se é a primeira vez que se abre o editTurnos deste projeto 
    # se for entao redirecionar para a seleção de aulas em paralelo
    if not Project.objects.values_list('has_selected_aulas_em_paralelo', flat=True).get(id=projId):
        return redirect(f'/parser/selecionar_aulas_em_paralelo/?id={projId}')

    #salas e docentes para dropdown select
    conn = sqlite3.connect('./database/Project'+ str(projId)+'/general_database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    stmt = ''' SELECT * FROM docentes ORDER BY abreviacao '''
    cursor.execute(stmt)
    docentesList = cursor.fetchall()

    stmt = ''' SELECT * FROM salas ORDER BY numero '''
    cursor.execute(stmt)
    salasList = cursor.fetchall()

    conn.close()

    #IR BUSCAR LISTA DE CURSOS ASSOCIADOS AO PROJETO
    cursos = auxfunc.getCursos(projId)
    cursos.sort()
    cursos_json = json.dumps(cursos)
    try:
        graph_controller.init_graph(projId)
        conflicts_unorg = graph_controller.get_organized_conflicts(projId)
        #print(f"-------conflicts_unorg: {conflicts_unorg}")
        conflicts = organizeInformation(projId, conflicts_unorg)
        # print(f"Conflicts: {conflicts}")
    except:
        #print("Could not load conflicts")
        conflicts = []
    return render(request, 'editTurnos/page.html', {'projetos':projetos, 'projId':projId, 'projeto':projeto, 'cursos': cursos_json,
                                                    'docentesList': docentesList, 'salasList': salasList, 'conflitos':conflicts, 'is_edit_turnos': True})

def fillPageForCursoAno(request):
    logger.info("fillPageForCursoAno view called")
    
    try:
        # Retira do request o nome do curso e do ano com os quais as tabelas serão preenchidas
        cursoNome = request.GET.get('curso')
        projId = int(request.GET.get('projId'))
        anoNum = int(request.GET.get('anoNum'))
        semanaInterval = request.GET.get('semanas', None)
        
        logger.debug(f"Request parameters - curso: {cursoNome}, projId: {projId}, anoNum: {anoNum}, semanaInterval: {semanaInterval}")

        start_date = None
        end_date = None

        if semanaInterval and semanaInterval != 'Semanas':
            start_date_str, end_date_str = semanaInterval.split(' - ')
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            logger.debug(f"Parsed dates - start_date: {start_date}, end_date: {end_date}")
        
        # Criar o objeto do tipo curso que contém docentes, anos, ucs e salas
        curso = Curso(cursoNome)
        logger.debug(f"Created Curso object for {cursoNome}")
        
        # Fazer fetch de todas as salas de um dado curso
        salasRows = auxfunc.getSalasFromCurso(projId, cursoNome)
        logger.debug(f"Retrieved {len(salasRows)} salas for curso {cursoNome}")
        
        salas = [ Sala(row['numero'], row['tipo'], row['capacidade']) for row in salasRows ]
        for sala in salas:
            # Fetch de todas as aulas de uma dada sala
            aulasSalaRows = auxfunc.getSalaHorario(projId, sala.numero)
            aulasSala = []
            for row in aulasSalaRows:
                semanaInicial = datetime.strptime(row['semanaInicial'], '%Y-%m-%d').date()
                semanaFinal = datetime.strptime(row['semanaFinal'], '%Y-%m-%d').date()
                if semanaInterval == None or semanaInterval == "Semanas" or areSemanasCompatible(semanaInicial, semanaFinal, start_date, end_date):
                    aulasSala.append(Aula(row['id'], row['horaInicial'], row['duracao'], row['diaSemana'], row['teorico'], row['semanaInicial'], row['semanaFinal']))
            
            for aula in aulasSala:
                turmasAula = auxfunc.getTurmasFromAula(projId, aula.id, cursoNome)
                aula.set_turmas(turmasAula) # FORMATO -> [codigoTurma]
            
            sala.set_aulas(aulasSala) # FORMATO -> [Aula]
            rendered_html = render_to_string('editTurnos/miniSchedule.html', {'dias': dias, 'horas': horas, 'aulas': aulasSala})
            minified_html = re.sub(r'>\s+<', '><', rendered_html)
            sala.set_miniHorario(minified_html)
            
            # Fetch de todos os blocos vermelhos de uma dada sala
            salaBlocoRows = auxfunc.getSalaBlocos(projId, sala.numero)
            salaBloco = [ Bloco(row['id'], row['hora'], row['diaSemana']) for row in salaBlocoRows]
            sala.set_blocos(salaBloco) # FORMATO -> [Bloco]
        
        curso.set_salas(salas)
        logger.debug(f"Processed {len(salas)} salas with their aulas and blocos")
        
        # Fazer fetch de todos os docentes de um curso
        docentesRows = auxfunc.getDocentesFromCurso(projId, cursoNome)
        logger.debug(f"Retrieved {len(docentesRows)} docentes for curso {cursoNome}")
        
        docentes = [ Docente(row['numeroMecanografico'], row['nome'], row['abreviacao']) for row in docentesRows]
        
        curso.set_docentes(docentes)
        
        # Fazer fetch de todas as ucs de um curso
        ucsRows = auxfunc.getUCsFromCurso(projId, cursoNome, anoNum)
        logger.debug(f"Retrieved {len(ucsRows)} UCs for curso {cursoNome} and ano {anoNum}")
        
        ucs = [ UC(row['codigo'], row['nome'], row['sigla']) for row in ucsRows ]
        for uc in ucs:
            # Fetch de todas as aulas de uma dada UC
            aulasUCRows = auxfunc.getUcHorario(projId, uc.codigo)
            aulasUC = []
            for row in aulasUCRows:
                semanaInicial = datetime.strptime(row['semanaInicial'], '%Y-%m-%d').date()
                semanaFinal = datetime.strptime(row['semanaFinal'], '%Y-%m-%d').date()
                if semanaInterval == None or semanaInterval == "Semanas" or (start_date and end_date and areSemanasCompatible(semanaInicial, semanaFinal, start_date, end_date)):
                    aulasUC.append(Aula(row['id'], row['horaInicial'], row['duracao'], row['diaSemana'], row['teorico'], row['semanaInicial'], row['semanaFinal']))
            for aula in aulasUC:
                turmasAula = auxfunc.getTurmasFromAula(projId, aula.id, cursoNome)
                aula.set_turmas(turmasAula) # FORMATO -> [codigoTurma]
            
            uc.set_aulas(aulasUC) # FORMATO -> [Aulas]
            
            anos = auxfunc.getAnoFromUcCurso(projId, cursoNome, uc.codigo)
            uc.set_anos(anos)
            
        curso.set_ucs(ucs)
        logger.debug(f"Processed {len(ucs)} UCs with their aulas and anos")
        
        # Fetch de todas as turmas de um dado ano
        turmasAno = auxfunc.getTurmasFromAnoCurso(projId, cursoNome, anoNum)
        turmasPorTurno = auxfunc.getTurmasPorTurnoCursoAno(projId, cursoNome, anoNum)
        logger.debug(f"Retrieved turmas - total: {len(turmasAno)}, por turno: {turmasPorTurno}")

        # Sort the list of turmas for each turno
        for turno, turmas in turmasPorTurno.items():
            turmas.sort()  # Sort in-place
            
        # Fetch de todos os docentes de um dado ano
        docentesAnoRows = auxfunc.getDocentesFromAnoFromCurso(projId, cursoNome, anoNum)
        docentesAno = [ Docente(row['numeroMecanografico'], row['nome'], row['abreviacao']) for row in docentesAnoRows]
        logger.debug(f"Retrieved {len(docentesAno)} docentes for ano {anoNum}")
        
        for docente in docentesAno:
            aulasDocenteRows = auxfunc.getDocenteHorario(projId, docente.numMecanografico)
            aulasDocente = []
            for row in aulasDocenteRows:
                semanaInicial = datetime.strptime(row['semanaInicial'], '%Y-%m-%d').date()
                semanaFinal = datetime.strptime(row['semanaFinal'], '%Y-%m-%d').date()
                if semanaInterval == None or semanaInterval == "Semanas" or (start_date and end_date and areSemanasCompatible(semanaInicial, semanaFinal, start_date, end_date)):
                    aulasDocente.append(Aula(row['id'], row['horaInicial'], row['duracao'], row['diaSemana'], row['teorico'], row['semanaInicial'], row['semanaFinal']))
            
            for aula in aulasDocente:
                turmasAula = auxfunc.getTurmasFromAula(projId, aula.id, cursoNome)
                aula.set_turmas(turmasAula) # FORMATO -> [codigoTurma]
            
            docente.set_aulas(aulasDocente)
            rendered_html = render_to_string('editTurnos/miniSchedule.html', {'dias': dias, 'horas': horas, 'aulas': aulasDocente} )
            minified_html = re.sub(r'>\s+<', '><', rendered_html)
            docente.set_miniHorario(minified_html)
            
            docenteBlocoRows = auxfunc.getDocenteBlocos(projId, docente.numMecanografico)
            docenteBloco = [ Bloco(row['id'], row['hora'], row['diaSemana']) for row in docenteBlocoRows]
            docente.set_blocos(docenteBloco)
            
        # Fetch de todas as semanas de um dado ano
        semanasAno = auxfunc.getSemanasFromCursoAno(projId, cursoNome, anoNum)
        logger.debug(f"Retrieved semanas for ano {anoNum}: {semanasAno}")

        ano = Ano(anoNum)
        ano.set_turmas(turmasAno)
        ano.set_turmasPorTurno(turmasPorTurno)
        ano.set_docentes(docentesAno)
        ano.set_semanas(semanasAno)
        anos = [ano]
        
        curso.set_anos(anos)

        # Fazer fetch da informação sobre turmas e turnos de um curso para cada ano
        numAnos = auxfunc.getNumYearsFromCurso(projId, cursoNome)
        logger.debug(f"Total number of anos for curso {cursoNome}: {numAnos}")
        
        # Por default, a página é carregada com informação correspondente ao primeiro ano existente do curso selecionado
        numeroTurmas = curso.anos[0].numTurmas
        turmasPorTurno = curso.anos[0].turmasPorTurno
        turmasAno = curso.anos[0].turmas
        semanasAno = curso.anos[0].semanas
        
        # Adicionar lista de UCs para o ano e curso atual
        ucs_ano = [{'codigo': uc.codigo, 'nome': uc.nome, 'sigla': uc.sigla} for uc in ucs]

        curso_encoder = CursoEncoder()
        curso_json = curso_encoder.encode(curso)

        response_data = {
            'schedulehtml': render(request, 'editTurnos/schedule.html', {'numeroTurmas': numeroTurmas, 'turmasPorTurno': turmasPorTurno, 
                                                                        'turmasAno': turmasAno, 'ano': anoNum, 'ucs': ucs}).content.decode(),
            'curso_json': curso_json,
            'numeroTurmas': numeroTurmas,
            'turmasAno': turmasAno,
            'turmasPorTurno': turmasPorTurno,
            'semanasAno': semanasAno,
            'numAnos': numAnos,
            'ucsAno': ucs_ano  # Adicionando a lista de UCs para o ano e curso selecionados
        }

        logger.info("Successfully processed fillPageForCursoAno request")
        return JsonResponse(response_data)

    except Exception as e:
        logger.error(f"Error in fillPageForCursoAno: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)



def uc_view(request: HttpRequest, projId: int, uc_codigo: str) -> HttpResponse:
    if not request.user.is_authenticated:
        return redirect('login/')
    
    projetos = getProjetosListAux(request, request.user.pk)
    projeto = Project.objects.values_list().get(id=projId)
    
    # Get UC information
    conn = sqlite3.connect(f'./database/Project{projId}/general_database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Get UC details
    cursor.execute('SELECT * FROM uc WHERE codigo = ?', (uc_codigo,))
    uc_info = cursor.fetchone()
    
    # Get all aulas for this UC
    aulas = auxfunc.getUcHorario(projId, uc_codigo)
    
    # Organize aulas by day
    aulas_por_dia = {
        'Segunda': [],
        'Terça': [],
        'Quarta': [],
        'Quinta': [],
        'Sexta': [],
        'Sábado': []
    }
    
    for aula in aulas:
        aula_dict = dict(aula)
        dia = aula_dict['diaSemana']
        
        # Get docentes for this aula
        aula_docentes = auxfunc.getAulaDocentes(projId, aula_dict['id'])
        aula_dict['docentes'] = []
        for docente_id in aula_docentes:
            cursor.execute('''SELECT numeroMecanografico, nome, abreviacao 
                            FROM docentes 
                            WHERE numeroMecanografico = ?''', (docente_id,))
            docente = cursor.fetchone()
            if docente:
                aula_dict['docentes'].append({
                    'id': docente['numeroMecanografico'],
                    'nome': docente['nome'],
                    'abreviacao': docente['abreviacao']
                })
        
        # Get salas for this aula
        aula_salas = auxfunc.getAulaSalas(projId, aula_dict['id'])
        aula_dict['salas'] = []
        for sala_num in aula_salas:
            cursor.execute('''SELECT numero, tipo 
                            FROM salas 
                            WHERE numero = ?''', (sala_num,))
            sala = cursor.fetchone()
            if sala:
                aula_dict['salas'].append(sala['numero'])
        
        aula_dict['salas_num'] = aula_dict['salas']  # For template compatibility
        aula_dict['docentes_abrev'] = [d['abreviacao'] for d in aula_dict['docentes']]
        
        if dia in aulas_por_dia:
            aulas_por_dia[dia].append(aula_dict)
    
    conn.close()
    
    context = {
        'projetos': projetos,
        'projId': projId,
        'projeto': projeto,
        'uc_info': uc_info,
        'aulas_por_dia': aulas_por_dia,
        'dias': ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"],
        'horas': horas,
        'is_edit_turnos': True,
    }
    
    return render(request, 'editTurnos/uc_view.html', context)

def get_uc_list(request):
    logger.debug("UC list requested - view entered")
    
    try:
        curso = request.GET.get('curso')
        ano = request.GET.get('ano')
        logger.debug(f"Request parameters: curso={curso}, ano={ano}")

        if not curso or not ano:
            logger.warning("Missing parameters in request")
            return JsonResponse({'error': 'Missing parameters'}, status=400)

        logger.debug("Querying database for UCs...")
        ucs = UC.objects.filter(curso=curso, ano=ano).values('codigo', 'nome')
        
        logger.debug(f"Found {len(ucs)} UCs")
        return JsonResponse({'uc_list': list(ucs)})
        
    except Exception as e:
        logger.error(f"Error in get_uc_list: {str(e)}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

def createEmptyTable(request):
    cursoNome = request.GET.get('curso')
    projId = int(request.GET.get('projId'))

    numAnos = auxfunc.getNumYearsFromCurso(projId, cursoNome)

    response_data = {
        'numAnos': numAnos
    }

    return JsonResponse(response_data)

def distribuicao_view(request):
    projId = int(request.GET.get('projId'))
    ucsLista = request.GET.get('ucsLista')
    if ucsLista:
        ucsLista = ucsLista.split(',')
    
    ucsDic = {}
    
    for ucCodigo in ucsLista:
        path = "Project" + str(projId)
        conn = sqlite3.connect('./database/' + path + '/general_database.db', check_same_thread=False)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        query = '''SELECT sigla FROM uc WHERE codigo = ?;'''
        cursor.execute(query, (ucCodigo,))
        result = cursor.fetchone()
        sigla = result['sigla']
        distribuicao = auxfunc.getDistribuicaoUC(projId, ucCodigo)
        ucsDic[sigla] = distribuicao  
        
    response_data = {
        'distribuicaohtml': render(request, 'editTurnos/vista_ucs_nsalas.html').content.decode(),
        'ucsDistribuicao': ucsDic
    }   
    return JsonResponse(response_data)

def schedule_view(request):    
    ano = request.GET.get('ano_obj')
    numeroTurnos = int(request.GET.get('numeroTurnos'))
    numeroTurmas = int(request.GET.get('numeroTurmas'))
    turmasPorTurnoString = request.GET.get('turmasPorTurno')
    turmasPorTurno = json.loads(turmasPorTurnoString)
    turmasPorTurno = {int(key): value for key, value in turmasPorTurno.items()}
    
    turmasAnoString = request.GET.get('turmasAno')
    turmasAno = json.loads(turmasAnoString)
    
    semanasAno = request.GET.get('semanasAno')
    
    context = {
        'ano': ano,
        'numeroTurnos': numeroTurnos,
        'numeroTurmas': numeroTurmas,
        'turmasPorTurno': turmasPorTurno,
        'turmasAno': turmasAno,
        'semanasAno': semanasAno
    }
    
    return render(request, 'editTurnos/schedule.html', context)

def blocosVermelhosTurma(request):
    projId = int(request.GET.get('projId'))
    turmaName = request.GET.get('turma')
    blocosRows = auxfunc.getTurmaBlocos(projId, turmaName)
    blocos = [
        {
            'id': row['id'],
            'hora': row['hora'],
            'diaSemana': row['diaSemana']
        }
        for row in blocosRows
    ]
    return JsonResponse({'blocos': blocos}, status=200)

def get_docente_horario(request):
    try:
        project_number = request.GET.get('projectNumber')
        docente_id = request.GET.get('docenteId')

        aulasDocenteRows = auxfunc.getDocenteHorario(project_number, docente_id)

        aulasDocente = [
            {
                'id': row['id'],
                'horaInicial': row['horaInicial'],
                'duracao': row['duracao'],
                'diaSemana': row['diaSemana'],
                'teorico': row['teorico'],
                'semanaInicial': row['semanaInicial'],
                'semanaFinal': row['semanaFinal']
            } for row in aulasDocenteRows
        ]
        
        return JsonResponse(aulasDocente, safe = False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    
def get_sala_horario(request):
    try:
        project_number = request.GET.get('projectNumber')
        numero_sala = request.GET.get('salaId')
        
        # Chama a função getSalaHorario e obtém os dados
        aulasSalaRows = auxfunc.getSalaHorario(project_number, numero_sala)
        
        # Converte os resultados para dicionário
        aulasSala = [
            {
                'id': row['id'],
                'horaInicial': row['horaInicial'],
                'duracao': row['duracao'],
                'diaSemana': row['diaSemana'],
                'teorico': row['teorico'],
                'semanaInicial': row['semanaInicial'],
                'semanaFinal': row['semanaFinal']
            } for row in aulasSalaRows
        ]
        
        return JsonResponse(aulasSala, safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def getDocenteMiniHorario(request):
    projNum = request.GET.get('projectNumber')
    docenteId = request.GET.get('docenteId')

    try:
        aulasDocenteRows = auxfunc.getDocenteHorario(projNum, docenteId)
        aulasDocente = [Aula(row['id'], row['horaInicial'], row['duracao'], row['diaSemana'], row['teorico'], row['semanaInicial'], row['semanaFinal']) for row in aulasDocenteRows]

        miniHorario = render_to_string('editTurnos/miniSchedule.html', {'dias': dias, 'horas': horas, 'aulas': aulasDocente})
        minified_html = re.sub(r'>\s+<', '><', miniHorario)
        response_data = {
            'docenteHorario': minified_html
        }
        return JsonResponse(response_data)
    except Exception as e:
        return JsonResponse({ 'error': str(e)}, status=500)
    
def getSalaMiniHorario(request):
    projNum = request.GET.get('projectNumber')
    salaId = request.GET.get('salaId')

    try:
        aulasSalaRows = auxfunc.getSalaHorario(projNum, salaId)
        aulasSala = [Aula(row['id'], row['horaInicial'], row['duracao'], row['diaSemana'], row['teorico'], row['semanaInicial'], row['semanaFinal']) for row in aulasSalaRows]

        miniHorario = render_to_string('editTurnos/miniSchedule.html', {'dias': dias, 'horas': horas, 'aulas': aulasSala})
        minified_html = re.sub(r'>\s+<', '><', miniHorario)
        response_data = {
            'salaHorario': minified_html
        }
        return JsonResponse(response_data)
    except Exception as e:
        return JsonResponse({ 'error': str(e)}, status=500)


def swap_teachers(request, projId):
    """
    Handles teacher swapping between two classes with improved error handling and logging.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"success": False, "error": "Unauthorized"}, status=401)
    
    try:
        # Parse request data with validation
        try:
            data = json.loads(request.body)
            aula1 = data.get('aula1', {})
            aula2 = data.get('aula2', {})
            teacher1 = data.get('teacher1')
            teacher2 = data.get('teacher2')
            
            if not all([aula1.get('id'), aula2.get('id'), teacher1, teacher2]):
                raise ValueError("Missing required parameters")
        except (json.JSONDecodeError, ValueError) as e:
            return JsonResponse({"success": False, "error": "Invalid request data"}, status=400)

        conn = sqlite3.connect(f'./database/Project{projId}/general_database.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute("BEGIN TRANSACTION")
            
            # Verify teachers exist and get their abbreviations
            cursor.execute('''SELECT numeroMecanografico, abreviacao 
                            FROM docentes 
                            WHERE numeroMecanografico IN (?, ?)''', 
                            (teacher1, teacher2))
            teachers = {str(row[0]): row[1] for row in cursor.fetchall()}
            
            if len(teachers) != 2:
                return JsonResponse({"success": False, "error": "One or both teachers not found"}, status=404)
            
            # Verify teachers are assigned to their respective aulas
            cursor.execute('''SELECT 1 FROM aulaDocente 
                            WHERE idAula = ? AND idDocente = ?''', 
                            (aula1['id'], teacher1))
            if not cursor.fetchone():
                return JsonResponse({"success": False, "error": "Teacher1 not assigned to aula1"}, status=400)
                
            cursor.execute('''SELECT 1 FROM aulaDocente 
                            WHERE idAula = ? AND idDocente = ?''', 
                            (aula2['id'], teacher2))
            if not cursor.fetchone():
                return JsonResponse({"success": False, "error": "Teacher2 not assigned to aula2"}, status=400)
            
            # Remove existing assignments
            cursor.execute('''DELETE FROM aulaDocente 
                            WHERE idAula = ? AND idDocente = ?''', 
                            (aula1['id'], teacher1))
            
            cursor.execute('''DELETE FROM aulaDocente 
                            WHERE idAula = ? AND idDocente = ?''', 
                            (aula2['id'], teacher2))
            
            # Create new assignments
            cursor.execute('''INSERT INTO aulaDocente (idAula, idDocente)
                            VALUES (?, ?)''', 
                            (aula1['id'], teacher2))
            
            cursor.execute('''INSERT INTO aulaDocente (idAula, idDocente)
                            VALUES (?, ?)''', 
                            (aula2['id'], teacher1))
            
            conn.commit()
            
            return JsonResponse({
                "success": True,
                "new_teacher1_abbreviation": teachers.get(teacher2),
                "new_teacher2_abbreviation": teachers.get(teacher1)
            })
            
        except sqlite3.Error as e:
            conn.rollback()
            return JsonResponse({
                "success": False, 
                "error": f"Database error: {str(e)}"
            }, status=500)
        finally:
            conn.close()
            
    except Exception as e:
        return JsonResponse({
            "success": False, 
            "error": f"Unexpected error: {str(e)}"
        }, status=500)

def swap_aulas(request, projId):
    """
    Handles swapping of two classes including their time slots and days.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"success": False, "error": "Unauthorized"}, status=401)
    
    try:
        data = json.loads(request.body)
        aula1 = data.get('aula1', {})
        aula2 = data.get('aula2', {})
        
        if not all([aula1.get('id'), aula2.get('id'), 
                   aula1.get('newDia'), aula2.get('newDia'),
                   aula1.get('newHora'), aula2.get('newHora')]):
            return JsonResponse({"success": False, "error": "Missing required parameters"}, status=400)

        conn = sqlite3.connect(f'./database/Project{projId}/general_database.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute("BEGIN TRANSACTION")
            
            # Update first aula
            cursor.execute('''
                UPDATE aula 
                SET diaSemana = ?, horaInicial = ?
                WHERE id = ?
            ''', (aula1['newDia'], aula1['newHora'], aula1['id']))
            
            # Update second aula
            cursor.execute('''
                UPDATE aula 
                SET diaSemana = ?, horaInicial = ?
                WHERE id = ?
            ''', (aula2['newDia'], aula2['newHora'], aula2['id']))
            
            conn.commit()
            
            # Check for conflicts
            conflicts1 = findAnyConflicts(projId, aula1['newDia'], aula1['newHora'], aula1['id'])
            conflicts2 = findAnyConflicts(projId, aula2['newDia'], aula2['newHora'], aula2['id'])
            all_conflicts = (conflicts1 or []) + (conflicts2 or [])
            
            return JsonResponse({
                "success": True,
                "conflicts": all_conflicts
            })
            
        except sqlite3.Error as e:
            conn.rollback()
            return JsonResponse({
                "success": False, 
                "error": f"Database error: {str(e)}"
            }, status=500)
        finally:
            conn.close()
            
    except Exception as e:
        return JsonResponse({
            "success": False, 
            "error": f"Unexpected error: {str(e)}"
        }, status=500)

def uc_changes(request, projId):
    """
    Handles:
    - Class time changes (move to empty cell)
    - Class swaps
    - Teacher swaps
    """
    if not request.user.is_authenticated:
        return JsonResponse({"success": False, "error": "Unauthorized"}, status=401)
    
    try:
        data = json.loads(request.body)
        change_type = data.get('type')  # 'move', 'swap', or 'teacher'
        
        conn = sqlite3.connect(f'./database/Project{projId}/general_database.db')
        cursor = conn.cursor()
        
        try:
            cursor.execute("BEGIN TRANSACTION")
            
            if change_type == 'move':
                # Handle moving class to empty cell
                aula_id = data.get('aulaId')
                new_dia = data.get('newDia')
                new_hora = data.get('newHora')
                if not all([aula_id, new_dia, new_hora]):
                    return JsonResponse({"success": False, "error": "Missing parameters"}, status=400)
                
                # Update aula position
                cursor.execute('''
                    UPDATE aula 
                    SET diaSemana = ?, horaInicial = ?
                    WHERE id = ?
                ''', (new_dia, new_hora, aula_id))
                
                conn.commit()
                
                # Check for conflicts
                conflicts = findAnyConflicts(projId, new_dia, new_hora, aula_id)
                return JsonResponse({
                    "success": True,
                    "conflicts": conflicts if conflicts else []
                })
                
            elif change_type == 'swap':
                # Handle class swaps (existing functionality)
                aula1 = data.get('aula1', {})
                aula2 = data.get('aula2', {})
                
                if not all([aula1.get('id'), aula2.get('id'), 
                           aula1.get('newDia'), aula2.get('newDia'),
                           aula1.get('newHora'), aula2.get('newHora')]):
                    return JsonResponse({"success": False, "error": "Missing parameters"}, status=400)
                
                # Update both aulas
                cursor.execute('''
                    UPDATE aula 
                    SET diaSemana = ?, horaInicial = ?
                    WHERE id = ?
                ''', (aula1['newDia'], aula1['newHora'], aula1['id']))
                
                cursor.execute('''
                    UPDATE aula 
                    SET diaSemana = ?, horaInicial = ?
                    WHERE id = ?
                ''', (aula2['newDia'], aula2['newHora'], aula2['id']))
                
                conn.commit()
                
                # Check for conflicts
                conflicts1 = findAnyConflicts(projId, aula1['newDia'], aula1['newHora'], aula1['id'])
                conflicts2 = findAnyConflicts(projId, aula2['newDia'], aula2['newHora'], aula2['id'])
                return JsonResponse({
                    "success": True,
                    "conflicts": (conflicts1 or []) + (conflicts2 or [])
                })
                
            elif change_type == 'teacher':
                # Handle teacher swaps (existing functionality)
                aula1 = data.get('aula1', {})
                aula2 = data.get('aula2', {})
                teacher1 = data.get('teacher1')
                teacher2 = data.get('teacher2')
                
                if not all([aula1.get('id'), aula2.get('id'), teacher1, teacher2]):
                    return JsonResponse({"success": False, "error": "Missing parameters"}, status=400)
                
                # Verify teachers exist
                cursor.execute('SELECT numeroMecanografico, abreviacao FROM docentes WHERE numeroMecanografico IN (?, ?)', 
                             (teacher1, teacher2))
                teachers = {str(row[0]): row[1] for row in cursor.fetchall()}
                
                if len(teachers) != 2:
                    return JsonResponse({"success": False, "error": "Teacher not found"}, status=404)
                
                # Remove existing assignments
                cursor.execute('DELETE FROM aulaDocente WHERE idAula = ? AND idDocente = ?', 
                              (aula1['id'], teacher1))
                cursor.execute('DELETE FROM aulaDocente WHERE idAula = ? AND idDocente = ?', 
                              (aula2['id'], teacher2))
                
                # Create new assignments
                cursor.execute('INSERT INTO aulaDocente (idAula, idDocente) VALUES (?, ?)', 
                              (aula1['id'], teacher2))
                cursor.execute('INSERT INTO aulaDocente (idAula, idDocente) VALUES (?, ?)', 
                              (aula2['id'], teacher1))
                
                conn.commit()
                return JsonResponse({
                    "success": True,
                    "new_teacher1_abbreviation": teachers.get(teacher2),
                    "new_teacher2_abbreviation": teachers.get(teacher1)
                })
                
            else:
                return JsonResponse({"success": False, "error": "Invalid change type"}, status=400)
                
        except sqlite3.Error as e:
            conn.rollback()
            return JsonResponse({"success": False, "error": f"Database error: {str(e)}"}, status=500)
        finally:
            conn.close()
            
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
# makeChanges
#
# Post Ajax request handler function
# receives the following post data:
#       - aulaId
#       - cadeiraId
#       - horaInicio
#       - duracao
#       - dia
#       - turmasIds -> list
#       - docentesIds -> list
#       - salasIds -> list
#
# loads current ones from db
# compares to find diferences
# makes apropriate changes
# checks for and returns conflicts 
def makeChanges(request, projId):
    global validator
    if (not request.user.is_authenticated):
        return JsonResponse({"error": "User is not authenticated", "id": projId}, status=401)
    if request.method != "POST" and not request.is_ajax():
        return JsonResponse({"error": "Invalid request", "id": projId}, status=400)

    #get request data
    body_unicode = request.body.decode('utf-8')
    data = json.loads(body_unicode)

    aulaId     = data['aulaId']
    cadeiraId  = data['cadeiraId']
    horaInicio = data['horaInicio']
    duracao = reverse_time_span_conversion(int(data['horaFim']) - int(horaInicio))
    dia        = switch_number_to_day(data['dia'])
    turmasIds  = data['turmasIds']
    docentesIds= [str(num) for num in data['docentesIds']]
    salasIds   = data['salasIds']

    #get original data for comparison
    conn = sqlite3.connect(f'./database/Project{projId}/general_database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    #horainicio, duracao, dia
    stmt = ''' SELECT horaInicial, duracao, diaSemana FROM aula WHERE id=?'''
    cursor.execute(stmt, [aulaId,])
    found = cursor.fetchone()

    horaInicio_origin = found['horaInicial']
    duracao_origin = found['duracao']
    dia_origin = found['diaSemana']

    #cadeira
    stmt= ''' SELECT idUC FROM aulaUC WHERE idAula = ?'''
    cursor.execute(stmt, [aulaId,])
    cadeiraId_origin = cursor.fetchone()['idUC']

    #turmas
    stmt= '''SELECT idTurma FROM aulaTurmas WHERE idAula=?'''
    cursor.execute(stmt, [aulaId,])
    turmasIds_origin = [row['idTurma'] for row in cursor.fetchall()]

    #docentes
    stmt= '''SELECT idDocente FROM aulaDocente WHERE idAula=?'''
    cursor.execute(stmt, [aulaId,])
    docentesIds_origin = [row['idDocente'] for row in cursor.fetchall()]

    #salas
    stmt= '''SELECT idSala FROM aulaSala WHERE idAula=?'''
    cursor.execute(stmt, [aulaId,])
    salasIds_origin = [row['idSala'] for row in cursor.fetchall()]

    #print(aulaId, cadeiraId_origin, horaInicio_origin, duracao_origin, dia_origin, turmasIds_origin, docentesIds_origin, salasIds_origin)

    #guardar booleanos
    cadeiraBool = False 
    duracaoBool = False
    diaHoraBool = False
    docenteBool = False
    salaBool = False
    turmaBool = False

    if cadeiraId != cadeiraId_origin:
        #trocar cadeira
        cadeiraBool = True
        changeUC(projId, aulaId, cadeiraId)
    if duracao != duracao_origin:
        #trocar duracao
        duracaoBool = True
        updateAulaDuration(projId, aulaId, duracao)
    if horaInicio != horaInicio_origin or dia != dia_origin:
        # trocar hora ou dia
        diaHoraBool = True
        moveAula(projId, aulaId, dia, horaInicio)
    for docente in [docente for docente in docentesIds if docente not in docentesIds_origin]:
        #adicionar docente
        docenteBool = True
        addDocente(projId, aulaId, docente)
    for docente in [docente for docente in docentesIds_origin if docente not in docentesIds]:
        #remover docente
        docenteBool = True
        removeDocente(projId, aulaId, docente)
    for sala in [sala for sala in salasIds if sala not in salasIds_origin]:
        #adicionar sala
        salaBool = True
        addSala(projId, aulaId, sala)
    for sala in [sala for sala in salasIds_origin if sala not in salasIds]:
        #remover sala
        salaBool = True
        removeSala(projId, aulaId, sala)
    for turma in [turma for turma in turmasIds if turma not in turmasIds_origin]:
        #adicionar turma
        turmaBool = True
        addTurma(projId, aulaId, turma)
    for turma in [turma for turma in turmasIds_origin if turma not in turmasIds]:
        #remover turma
        turmaBool = True
        removeTurma(projId, aulaId, turma)

    validator = False
    checkConflict = findAnyConflicts(projId, dia, horaInicio, aulaId)
    #buscar conflitos e envia-los
    if (checkConflict == 0):
        conflicts = []
    else:
        conflicts = checkConflict
    return JsonResponse({
        "aulaId" : aulaId,
        "id": projId, 
        "conflicts": conflicts, 
    }, status=200)

def getAulaSimultaneasParalelas(request):    
    try:
        projId = int(request.GET.get('projId'))
        aulaId_1 = request.GET.get('aulaId_1')
        aulaId_2 = request.GET.get('aulaId_2')
        aulaId_1 = int(aulaId_1) if aulaId_1 and aulaId_1 != 'null' else None
        aulaId_2 = int(aulaId_2) if aulaId_2 and aulaId_2 != 'null' else None

        if (not request.user.is_authenticated):
            return JsonResponse({"error": "User is not authenticated", "id": projId}, status=401)
        if request.method != "GET" and not request.is_ajax():
            return JsonResponse({"error": "Invalid request", "id": projId}, status=400)

        conn = sqlite3.connect(f'./database/Project{projId}/general_database.db')
        cursor = conn.cursor()

        show_popup_paralelo = False
        show_popup_simultanea = False
        ambas_pertencem_a_grupos_diferentes = False
        show_popup_aula_em_paralelo_e_simultanea = False
        grupo_paralelo = []
        grupo_simultanea = []
        segundo_grupo_paralelo = []     # os segundos grupos são para o caso de cada uma das aulas pertencer a grupos diferentes
        segundo_grupo_simultanea = []   # de aulas em paralelo ou em simultaneo
        # TODOO check show_popup_aula_em_paralelo_e_simultanea!!
        # for aulas em paralelo
        if aulaId_1 is not None:
            cursor.execute("SELECT COUNT(*) FROM turmasSimultaneas WHERE aula1 = ? OR aula2 = ?", [aulaId_1, aulaId_1])
            show_popup_paralelo = cursor.fetchone()[0] > 0
            grupo_paralelo = obter_grupo_de_aulas(aulaId_1, 'turmasSimultaneas', projId)
            if (not show_popup_paralelo) and (aulaId_2 is not None):
                cursor.execute("SELECT COUNT(*) FROM turmasSimultaneas WHERE aula1 = ? OR aula2 = ?", [aulaId_2, aulaId_2])
                show_popup_paralelo = cursor.fetchone()[0] > 0
                grupo_paralelo = obter_grupo_de_aulas(aulaId_2, 'turmasSimultaneas', projId)
        elif aulaId_2 is not None:
            cursor.execute("SELECT COUNT(*) FROM turmasSimultaneas WHERE aula1 = ? OR aula2 = ?", [aulaId_2, aulaId_2])
            show_popup_paralelo = cursor.fetchone()[0] > 0
            grupo_paralelo = obter_grupo_de_aulas(aulaId_2, 'turmasSimultaneas', projId)

        # for aulas simultâneas
        if aulaId_1 is not None:
            cursor.execute("SELECT COUNT(*) FROM aulasSimultaneas WHERE aula1 = ? OR aula2 = ?", [aulaId_1, aulaId_1])
            show_popup_simultanea = cursor.fetchone()[0] > 0
            grupo_simultanea = obter_grupo_de_aulas(aulaId_1, 'aulasSimultaneas', projId)
            if (not show_popup_simultanea) and (aulaId_2 is not None):
                cursor.execute("SELECT COUNT(*) FROM aulasSimultaneas WHERE aula1 = ? OR aula2 = ?", [aulaId_2, aulaId_2])
                show_popup_simultanea = cursor.fetchone()[0] > 0
                grupo_simultanea = obter_grupo_de_aulas(aulaId_2, 'aulasSimultaneas', projId)
        elif aulaId_2 is not None:
            cursor.execute("SELECT COUNT(*) FROM aulasSimultaneas WHERE aula1 = ? OR aula2 = ?", [aulaId_2, aulaId_2])
            show_popup_simultanea = cursor.fetchone()[0] > 0
            grupo_simultanea = obter_grupo_de_aulas(aulaId_2, 'aulasSimultaneas', projId)

        if (grupo_simultanea and grupo_paralelo):
            # se uma das aulas pertencer a um grupo em paralelo e a outra for uma aula em simultâneo
            ambas_pertencem_a_grupos_diferentes = True

        # check if it's a change between two classes of the same group
        # if it is then it's okay to ignore and treat as a regular change
        # else if it's a change between two classes of different groups then ambas_pertencem_a_grupos_diferentes is true
        if (aulaId_1 is not None) and (aulaId_2 is not None):
            grupo_paralelo_id = {aula["id"] for aula in grupo_paralelo} # grupo_paralelo but it's just a list of ids
            grupo_simultanea_id = {aula["id"] for aula in grupo_simultanea} # grupo_simultanea but it's just a list of ids

            if (aulaId_1 in grupo_paralelo_id) and (aulaId_2 in grupo_paralelo_id): 
                # se as duas aulas estiverem no mesmo grupo de aulas em paralelo
                show_popup_paralelo = False
            else:
                cursor.execute("SELECT COUNT(*) FROM turmasSimultaneas WHERE aula1 = ? OR aula2 = ?", [aulaId_1, aulaId_1])
                aula1_paralelo = cursor.fetchone()[0] > 0
                cursor.execute("SELECT COUNT(*) FROM turmasSimultaneas WHERE aula1 = ? OR aula2 = ?", [aulaId_2, aulaId_2])
                aula2_paralelo = cursor.fetchone()[0] > 0
                if (aula1_paralelo and aula2_paralelo):
                    # se as duas aulas forem aulas em paralelo mas em grupos diferentes
                    ambas_pertencem_a_grupos_diferentes = True
                    segundo_grupo_paralelo = obter_grupo_de_aulas(aulaId_2, 'turmasSimultaneas', projId)
                
            if (aulaId_1 in grupo_simultanea_id) and (aulaId_2 in grupo_simultanea_id):
                # se as duas aulas estiverem no mesmo grupo de aulas em simultaneo
                show_popup_simultanea = False
            else:
                cursor.execute("SELECT COUNT(*) FROM aulasSimultaneas WHERE aula1 = ? OR aula2 = ?", [aulaId_1, aulaId_1])
                aula1_simultanea = cursor.fetchone()[0] > 0
                cursor.execute("SELECT COUNT(*) FROM aulasSimultaneas WHERE aula1 = ? OR aula2 = ?", [aulaId_2, aulaId_2])
                aula2_simultanea = cursor.fetchone()[0] > 0
                if (aula1_simultanea and aula2_simultanea):
                    # se as duas aulas forem aulas em simultâneo mas em grupos diferentes
                    ambas_pertencem_a_grupos_diferentes = True
                    segundo_grupo_paralelo = obter_grupo_de_aulas(aulaId_2, 'turmasSimultaneas', projId)

        return JsonResponse({
            'paralelo': show_popup_paralelo,
            'simultanea': show_popup_simultanea,
            'grupo_paralelo': grupo_paralelo,
            'grupo_simultanea': grupo_simultanea,
            'ambas_pertencem_a_grupos_diferentes': ambas_pertencem_a_grupos_diferentes,
            'aula_paralelo_e_simultanea': show_popup_aula_em_paralelo_e_simultanea,
            'segundo_grupo_paralelo': segundo_grupo_paralelo,
            'segundo_grupo_simultanea': segundo_grupo_simultanea
        }, status=200)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def obter_grupo_de_aulas(aula_id, table, proj_id):
    """
    Dado o id da aula, o id do projeto e a tabela relacional (turmasSimultaneas ou aulasSimultaneas),
    retorna uma lista das aulas do grupo com detalhes: id, curso, uc, salas, turmas, professores.
    """
    if table not in ('turmasSimultaneas', 'aulasSimultaneas'):
        return f"ERRO: tabela inválida '{table}'. Tem de ser turmasSimultaneas ou aulasSimultaneas."

    db_path = os.path.join(settings.BASE_DIR, "database", f"Project{proj_id}", "general_database.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Obter os pares de aulas ligadas
        cursor.execute(f'SELECT aula1, aula2 FROM {table}')
        pares = cursor.fetchall()

        # Criar grafo de ligações
        adj = defaultdict(set)
        for row in pares:
            a1, a2 = int(row["aula1"]), int(row["aula2"])
            adj[a1].add(a2)
            adj[a2].add(a1)

        # Fazer BFS para encontrar todas as aulas do grupo
        if aula_id not in adj:
            grupo_ids = [aula_id]
        else:
            visitados = set()
            fila = deque([aula_id])
            grupo_ids = []

            while fila:
                atual = fila.popleft()
                if atual in visitados:
                    continue
                visitados.add(atual)
                grupo_ids.append(atual)
                fila.extend(adj[atual] - visitados)

        # Obter os detalhes de cada aula
        resultados = []
        for aid in sorted(grupo_ids):
            # Obter UC associada à aula
            cursor.execute("""
                SELECT uc.codigo AS cod_uc, uc.nome AS nome_uc, uc.idCurso AS curso_abv
                FROM aulaUC
                LEFT JOIN uc ON uc.codigo = aulaUC.idUC
                WHERE aulaUC.idAula = ?
            """, (aid,))
            uc_info = cursor.fetchone()

            # Obter salas
            cursor.execute("""
                SELECT s.numero FROM aulaSala
                JOIN salas s ON s.numero = aulaSala.idSala
                WHERE aulaSala.idAula = ?
            """, (aid,))
            salas = [row["numero"] for row in cursor.fetchall()]

            # Obter turmas
            cursor.execute("""
                SELECT t.codigo FROM aulaTurmas
                JOIN turmas t ON t.codigo = aulaTurmas.idTurma
                WHERE aulaTurmas.idAula = ?
            """, (aid,))
            turmas = [row["codigo"] for row in cursor.fetchall()]

            # Obter docentes
            cursor.execute("""
                SELECT d.nome FROM aulaDocente
                JOIN docentes d ON d.numeroMecanografico = aulaDocente.idDocente
                WHERE aulaDocente.idAula = ?
            """, (aid,))
            docentes = [row["nome"] for row in cursor.fetchall()]

            resultados.append({
                "id": aid,
                "curso": uc_info["curso_abv"] if uc_info else None,
                "uc": uc_info["nome_uc"] if uc_info else None,
                "sala": ", ".join(salas) if salas else None,
                "turmas": turmas,
                "docentes": docentes
            })

        return resultados

    finally:
        conn.close()


# editDocentes
#
# renders the edit docentes page, with a list of all docentes in the project
def editDocentes(request, projId):
    if (not request.user.is_authenticated):
        return redirect('login/')
    
    #projetos = Project.objects.filter(person = Person.objects.get(username = request.user.pk))
    projetos = getProjetosListAux(request, request.user.pk)

    conn = sqlite3.connect('./database/Project'+ str(projId)+'/general_database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    stmt = ''' SELECT * FROM docentes ORDER BY abreviacao '''
    cursor.execute(stmt)
    docentesList = cursor.fetchall()

    return render(request, 'editTurnos/editDocentes.html', {'docentes' : docentesList, 'projetos': projetos, 'projId':projId, 'is_edit_turnos': True})


# editDocentesMakeChange
#
# Post Ajax request handler function
#
# Receives the old Docente id, new docente id, new docente name, new docente sigla
# Checks if the new id is not already taken
# updates the entry on the database
def editDocentesMakeChange(request, projId):
    if (not request.user.is_authenticated):
        return JsonResponse({"error": "User is not authenticated", "id": projId}, status=401)
    if request.method != "POST" and not request.is_ajax():
        return JsonResponse({"error": "Invalid request", "id": projId}, status=400)

    body_unicode = request.body.decode('utf-8')
    data = json.loads(body_unicode)

    idDocente    = data['idDocente']
    nomeDocente  = bleach.clean(data['nomeDocente'])
    siglaDocente = bleach.clean(data['siglaDocente'])
    oldId        = data['oldId']

    conn = sqlite3.connect('./database/Project'+ str(projId)+'/general_database.db')
    cursor = conn.cursor()

    #print(f'editDocentesMakeChange: projId: {projId}, idDocente: {idDocente}, nomeDocente: {nomeDocente}, siglaDocente:{siglaDocente}, oldIdDocente: {oldId}')

    stmt = ''' SELECT numeroMecanografico FROM docentes WHERE numeroMecanografico = ?'''
    cursor.execute(stmt, [idDocente,])
    ids = cursor.fetchall()

    #check if id is available
    if oldId!=idDocente and len(ids)>0:
        return JsonResponse({"error": "Número Mecanográfico já em uso!"}, status=409)
    
    stmt= '''UPDATE docentes SET numeroMecanografico=?, nome=?, abreviacao=? WHERE numeroMecanografico=?'''
    cursor.execute(stmt, (idDocente, nomeDocente, siglaDocente, oldId))
    conn.commit()
    return JsonResponse({'idDocente': idDocente, 'nomeDocente':nomeDocente, 'siglaDocente': siglaDocente}, status=200)


# createDocente
#
# Post Ajax request handler function
#
# Receives the Docente id, name and sigla
# Checks if the id is not already taken
# creates the entry on the database, if possible
def createDocente(request, projId):
    if (not request.user.is_authenticated):
        return JsonResponse({"error": "User is not authenticated", "id": projId}, status=401)
    if request.method != "POST" and not request.is_ajax():
        return JsonResponse({"error": "Invalid request", "id": projId}, status=400)
    
    idDocente = request.POST.get('idDocente')
    nomeDocente = bleach.clean(request.POST.get('nomeDocente'))
    siglaDocente = bleach.clean(request.POST.get('siglaDocente'))

    conn = sqlite3.connect(f'./database/Project{projId}/general_database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    stmt = ''' SELECT * FROM docentes WHERE numeroMecanografico = ?'''
    cursor.execute(stmt, [idDocente,])
    ids = cursor.fetchall()

    #check if id is available
    if len(ids) >0:
        return JsonResponse({"error": "Número Mecanográfico já em uso!"}, status=409)
    
    try:
        stmt= '''INSERT INTO docentes (numeroMecanografico, nome, abreviacao) VALUES (?, ?, ?)'''
        cursor.execute(stmt, (idDocente, nomeDocente, siglaDocente))
        conn.commit()
        return JsonResponse({'idDocente': idDocente, 'nomeDocente':nomeDocente, 'siglaDocente': siglaDocente}, status=200)
    except:
        return JsonResponse({"error": "Não foi possível criar o docente."}, status=500)

# reverse_time_span_conversion
#
# auxiliary function that receives the duration 
# and convertes it the corresponding rowspan
def reverse_time_span_conversion(time_span):
    if time_span % 100 == 30:
        time_span = (time_span - 30) / 100 * 2 + 1
    else:
        time_span = time_span / 100 * 2
    return int(time_span + 0.5)

# switch_number_to_day
#
# Auxiliary function that receives a number as a string
# and converts it to the corresponding week day string
def switch_number_to_day(number_string):
    switch_dict = {
        '0' : 'Segunda',
        '1' : 'Terça',
        '2' : 'Quarta',
        '3' : 'Quinta',
        '4' : 'Sexta',
        '5' : 'Sábado'
    }
    return switch_dict.get(number_string, None)

# export
#
# loads the changes between the projects general and initial databases
# and renders the export page for the project
def get_aula_info(projId, aulaId):
    """
    Retrieves complete AulaInfo for a specific aula from the project database
    Returns an AulaInfo object or None if not found
    """
    conn = sqlite3.connect(f'./database/Project{projId}/general_database.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Get basic aula information
        cursor.execute('''
            SELECT a.id, a.horaInicial, a.duracao, a.diaSemana,
                   GROUP_CONCAT(DISTINCT asl.idSala) as salas_ids,
                   GROUP_CONCAT(DISTINCT ad.idDocente) as docentes_ids,
                   GROUP_CONCAT(DISTINCT at.idTurma) as turmas_ids,
                   uc.codigo as cadeiraId, uc.nome as uc_name
            FROM aula a
            LEFT JOIN aulaSala asl ON a.id = asl.idAula
            LEFT JOIN aulaDocente ad ON a.id = ad.idAula
            LEFT JOIN aulaTurmas at ON a.id = at.idAula
            JOIN aulaUC auc ON a.id = auc.idAula
            JOIN uc ON auc.idUC = uc.codigo
            WHERE a.id = ?
            GROUP BY a.id
        ''', [aulaId])
        
        aula_data = cursor.fetchone()
        
        if not aula_data:
            return None

        # Prepare the data dictionary for AulaInfo
        row_dict = {
            "id": aula_data['id'],
            "horaInicial": aula_data['horaInicial'],
            "duracao": aula_data['duracao'],
            "diaSemana": aula_data['diaSemana'],
            "idUc": aula_data['cadeiraId'],
            "idTurma": aula_data['turmas_ids'].split(',')[0] if aula_data['turmas_ids'] else None,
            "idDocente": aula_data['docentes_ids'].split(',')[0] if aula_data['docentes_ids'] else None,
            "idSala": aula_data['salas_ids'].split(',')[0] if aula_data['salas_ids'] else None
        }

        # Process the base data
        data = append_aula_data(row_dict)
        
        # Add the collected relationships
        data.update({
            'turmasIds': aula_data['turmas_ids'].split(',') if aula_data['turmas_ids'] else [],
            'docentesIds': [str(d) for d in aula_data['docentes_ids'].split(',')] if aula_data['docentes_ids'] else [],
            'salasIds': aula_data['salas_ids'].split(',') if aula_data['salas_ids'] else [],
        })

        # Create and return the AulaInfo instance
        aula = AulaInfo.from_data(data)
        aula.uc_name = aula_data['uc_name'] if aula_data['uc_name'] else ''
        return aula
        
    except Exception as e:
        print(f"Error fetching aula info: {e}")
        return None
    finally:
        conn.close()

def getConflicts(request, projId):
    global validator
    if not request.user.is_authenticated:
        return redirect('login/')

    projetos = getProjetosListAux(request, request.user.pk)
    projeto = Project.objects.values_list().get(id=projId)

    manager = organize_changes(projId, "general", validator)
    validator = True  # Reset validator for next use
    
    # Build conflicts dictionary {main_aula_id: [conflicting_aula_info1, conflicting_aula_info2]}
    conflicts_dict = {}
    all_conflicts = set()
    for node in manager.get_all_nodes():
        if node.dependency_ids:
            main_info = get_aula_info(projId, node.change.new.id)
            all_conflicts.add(main_info)
            conflicts = []
            for conflict_id in node.dependency_ids:
                conflict_node = manager.get_node_by_aula_id(conflict_id)
                conflict_info = get_aula_info(projId, conflict_id)
                all_conflicts.add(conflict_info)
                conflicts.append(conflict_info)
            if conflicts:
                conflicts_dict[main_info] = conflicts

    path = f"Project{projId}"
    db_path = f'./database/{path}/general_database.db'
    connDB = sqlite3.connect(db_path, check_same_thread=False)
    connDB.row_factory = sqlite3.Row
    cursorDB = connDB.cursor()

    for aula in all_conflicts:
        cursorDB.execute(f"""
        SELECT d.numeroMecanografico, d.nome
        FROM aulaDocente ad 
        JOIN docentes d ON ad.idDocente = d.numeroMecanografico
        WHERE ad.idAula = {aula.id};
        """)
        names_new = [row[1] for row in cursorDB.fetchall()]
        aula.set_docentes_names(names_new)


    conflict_manager = Conflict_Manager(projId, all_conflicts)
    conflict_manager.grouping()
    
    
    
    return render(request, 'export/conflicts.html', {
        'projeto': projeto[2],
        'projId': projId,
        'conflicts_turmas': conflict_manager.conflicts_turmas,
        'conflicts_salas': conflict_manager.conflicts_salas,
        'conflicts_docentes': conflict_manager.conflicts_docentes,
        'has_conflicts': bool(conflicts_dict)
    })
    
def export(request, projId):
    global validator
    if not request.user.is_authenticated:
        return redirect('login/')

    projetos = getProjetosListAux(request, request.user.pk)
    projeto = Project.objects.values_list().get(id=projId)

    manager = organize_changes(projId, "initial", validator)
    validator = True  # Reset validator for next use
    # Get the list of (node, counter) tuples
    node_counter_dict = manager.get_all_nodes_with_counter()
    for node_id in node_counter_dict:
        node = manager.get_node(node_id)
        if node.dependency_ids and node.conflict_ids != []:
            tmp = []
            for conflict in node.dependency_ids:
                conflict_node = manager.get_node_by_aula_id(conflict)
                if conflict_node is not None:
                    print(f"Conflict_id -> {conflict_node.id}")
                    tmp.append(node_counter_dict[conflict_node.id])
            node.dependencies = tmp
    # Count unsolved conflicts
    unsolved_conflicts = 0
    for uc in manager.ucs:
        unsolved_conflicts += len(manager.ucs[uc].unsolved_nodes)
    print(f"Unsolved conflicts: {unsolved_conflicts}")
    return render(request, 'export/page.html', {
        'projetos': projetos,
        'projeto': projeto[2], # obter nome do projeto  
        'manager' : manager,
        'ucs': manager.ucs,
        'ucs_ordered': manager.ordered_list,
        'projId': projId,
        'is_edit_turnos': False,
        'node_counter_list': node_counter_dict  # <-- Add this line
    })
