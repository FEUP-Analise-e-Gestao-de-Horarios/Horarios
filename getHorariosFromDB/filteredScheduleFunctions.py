import sqlite3
import getHorariosFromDB.auxiliaryScheduleFunctions as sch
#import auxiliaryScheduleFunctions as sch


# {docente: [aula, aula, aula]}
def getHorariosFromDocentesFromCurso(ProjectNumber, Curso):
    listaDeHorarios = {}
    lista_docentes = sch.getDocentesFromCurso(ProjectNumber, Curso)
    for docente in lista_docentes:
        listaDeHorarios[docente['numeroMecanografico']] = sch.getDocenteHorario(ProjectNumber, docente['numeroMecanografico'])
    return listaDeHorarios


# {turma: [aula, aula, aula]}
def getHorariosFromTurmasFromCurso(ProjectNumber, Curso):
    listaDeHorarios = {}
    lista_turmas = sch.getTurmasFromCurso(ProjectNumber, Curso)
    for turma in lista_turmas:
        listaDeHorarios[turma['codigo']] = sch.getTurmaHorario(ProjectNumber, turma['codigo'])
    return listaDeHorarios

# {uc: [aula, aula, aula]}
def getHorariosFromUCsFromCurso(ProjectNumber, Curso):
    listaDeHorarios = {}
    lista_ucs = sch.getUCsFromCurso(ProjectNumber, Curso)
    for uc in lista_ucs:
        listaDeHorarios[uc['cod_uc']] = sch.getUcHorario(ProjectNumber, uc['cod_uc'])
    return listaDeHorarios

# {turno: {turma: [aula, aula, aula]}}
def getHorariosFromTurmasFromTurnoFromCurso(ProjectNumber, Curso):
    listaDeHorarios={}
    lista_turmas = sch.getTurmasFromTurno(ProjectNumber, Curso)
    for turno in lista_turmas:
        horariosDasTurmas = {}
        for turma in turno[1].split(","): 
            horariosDasTurmas[turma] = sch.getTurmaHorario(ProjectNumber, turma)
        listaDeHorarios[turno[0]] = horariosDasTurmas
    return listaDeHorarios

# {UC: [aula, aula, aula]}
def getDistribuicaoFromUCFromCurso(ProjectNumber, Curso):
    listaDeDistribuicao={}
    listaDeUCs = sch.getUCsFromCurso(ProjectNumber, Curso)
    for uc in listaDeUCs:
        listaDeDistribuicao[uc] = sch.getDistribuicaoUC(ProjectNumber, uc)
    return listaDeDistribuicao

# int
def getNumeroTurnos(ProjectNumber, Curso):
    return len(getHorariosFromTurmasFromTurnoFromCurso(ProjectNumber, Curso))

# int
def getNumeroTurmas(ProjectNumber, Curso, Ano):
    numTurmas = sch.getNumeroTurmasAno(ProjectNumber, Curso, Ano)
    return numTurmas
