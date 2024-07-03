class Curso:
    def __init__(self, nome):
        self.nome = nome
        
    def set_docentes(self, docentes):
        self.docentes = docentes
        
    def set_anos(self, anos):
        self.anos = anos
        
    def set_ucs(self, ucs):
        self.ucs = ucs
        
    def set_salas(self, salas):
        self.salas = salas

class Ano:
    def __init__(self, ano):
        self.ano = ano
    
    def set_turmas(self, turmas):
        self.turmas = turmas
        self.numTurmas = len(turmas)
        
    def set_turmasPorTurno(self, turmasTurno):
        self.turmasPorTurno = turmasTurno
        
    def set_docentes(self, docentes):
        self.docentes = docentes
    
    def set_semanas(self, semanas):
        self.semanas = semanas

class Docente:
    def __init__(self, numMecanografico, nome, abrev):
        self.numMecanografico = numMecanografico
        self.nome = nome
        self.abreviacao = abrev
        self.aulas = []
        self.blocos = []
        self.miniHorario = ""
        
    def set_aulas(self, aulas):
        self.aulas = aulas

    def set_blocos(self, blocos):
        self.blocos = blocos

    def set_miniHorario(self, miniHorario):
        self.miniHorario = miniHorario
        
class UC:
    def __init__(self, codigo, nome, sigla):
        self.codigo = codigo
        self.nome = nome
        self.sigla = sigla
        
    def set_anos(self, anos):
        self.anos = anos
        
    def set_aulas(self, aulas):
        self.aulas = aulas
        
class Aula:
    def __init__(self, id, horaInicial, duracao, diaSemana, isTeorica, semanaInicial, semanaFinal):
        self.id = id
        self.horaInicial = horaInicial
        self.duracao = duracao
        self.diaSemana = diaSemana
        self.isTeorica = isTeorica
        self.semanaInicial = semanaInicial
        self.semanaFinal = semanaFinal
    
    def set_turmas(self, turmas):
        self.turmas = turmas
        
class Sala:
    def __init__(self, numero, tipo, capacidade):
        self.numero = numero
        self.tipo = tipo
        self.capacidade = capacidade
        
    def set_aulas(self, aulas):
        self.aulas = aulas
        
    def set_blocos(self, blocos):
        self.blocos = blocos

class Bloco:
    def __init__(self, id, hora, diaSemana):
        self.id = id
        self.hora = hora
        self.diaSemana = diaSemana        