from . import utils

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
        self.miniHorario = ""
        
    def set_aulas(self, aulas):
        self.aulas = aulas
        
    def set_blocos(self, blocos):
        self.blocos = blocos

    def set_miniHorario(self, miniHorario):
        self.miniHorario = miniHorario

class Bloco:
    def __init__(self, id, hora, diaSemana):
        self.id = id
        self.hora = hora
        self.diaSemana = diaSemana

class AulaInfo:
    def __init__(self, aula_id=None, cadeira_id=None, hora_inicio=None, hora_fim=None, dia=None, 
                 turmas_ids=None, docentes_ids=None, salas_ids=None, uc_name=None):
        self.id = aula_id
        self.cadeira_id = cadeira_id
        self.uc_name = uc_name
        self.hora_inicio = hora_inicio
        self.hora_fim = hora_fim
        self.dia = dia
        self.turmas_ids = turmas_ids
        self.docentes_ids = docentes_ids
        self.salas_ids = salas_ids
        self.docentes_names = []

    @staticmethod
    def from_data(data):
        """Create an AulaInfo instance from the provided data."""
        
        # Extract all necessary values directly from the data
        aula_id = data['aulaId']
        cadeira_id = data['cadeiraId']
        hora_inicio = data['horaInicio']
        hora_fim = data['horaFim']

        turmas_ids = data['turmasIds']
        docentes_ids = [str(num) for num in data['docentesIds']]
        salas_ids = data['salasIds']
        
        dia = data['dia']
        # Return a new AulaInfo object
        return AulaInfo(
            aula_id=aula_id,
            cadeira_id=cadeira_id,
            hora_inicio=hora_inicio,
            hora_fim=hora_fim,
            dia=dia,
            turmas_ids=turmas_ids,
            docentes_ids=docentes_ids,
            salas_ids=salas_ids,
        )
    def set_docentes_names(self, docentes_names):
        self.docentes_names = docentes_names

    def formatted_time(self):
        """Return the time range in a formatted string."""
        return f"{self.hora_inicio} - {self.hora_fim}"
    
    def formatted_day(self):
        """Return the day name from the day number."""
        days = ["Segunda", "Terca", "Quarta", "Quinta", "Sexta"]
        return days[self.dia] if 0 <= self.dia < len(days) else "Unknown"

    def day_index(self):
        """Return the day number from the day name string."""
        days = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta"]

        if isinstance(self.dia, str):
            return days.index(self.dia) if self.dia in days else -1
        else:
            return -1

    def formatted_salas(self):
        """Return a comma-separated list of rooms."""
        return ", ".join(str(sala) for sala in self.salas_ids)
    
    def formatted_docentes(self):
        """Return a comma-separated list of docentes."""
        return ", ".join(str(docente) for docente in self.docentes_names) if self.docentes_names else ", ".join(str(docente) for docente in self.docentes_ids)

    def formatted_turmas(self):
        """Return a comma-separated list of turmas."""
        return ", ".join(str(turma) for turma in self.turmas_ids)

    def to_dict(self):
        return {
            'aulaId': self.id,
            'cadeiraId': self.cadeira_id,
            'horaInicio': self.hora_inicio,
            'horaFim': self.hora_fim,
            'dia': self.dia,
            'turmasIds': self.turmas_ids,
            'docentesIds': self.docentes_ids,
            'salasIds': self.salas_ids,
            'uc_name': self.uc_name
        }

    
    def __str__(self):
        """Human-friendly string representation."""
        return (f"AulaInfo(id={self.id}, cadeira_id={self.cadeira_id}, hora_inicio={self.hora_inicio}, "
                f"hora_fim={self.hora_fim}, dia={self.dia}, "
                f"turmas_ids={self.turmas_ids}, docentes_ids={self.docentes_ids}, salas_ids={self.salas_ids})")
    
    def __hash__(self):
        return hash(self.id)
    
    def __eq__(self, other):
        if not isinstance(other, AulaInfo):
            return False
        return self.id == other.id
#This class represents a change in the aula info
    #previous -> Information about the original aula
    #new -> Information about the new aula info
    #type -> 0: only one aula is considered | 1: a change between 2 different classes

#class AulaGroups:
        #Both the cases below are detected in the initial database and should be 
            #caso especial aulas ids diferentes mas com sala+hora_inicio+duracao iguais representa caso especial (pode ter mais do que uma aula)
            #caso especial cadeiras com 2 ou mais uc+hora+duracao iguais
        

class AulaChange:
    def __init__(self, previous: AulaInfo, new: AulaInfo):
        self.previous = previous
        self.new = new

    def check_dia(self):
        return self.previous.dia != self.new.dia
    
    def check_docentes(self):
        return set(self.previous.docentes_ids) != set(self.new.docentes_ids)
    
    def check_turmas(self):
        return set(self.previous.turmas_ids) != set(self.new.turmas_ids)

    def check_salas(self):
        return set(self.previous.salas_ids) != set(self.new.salas_ids)
    
    def check_horario(self):
        return self.previous.hora_inicio != self.new.hora_inicio or self.previous.hora_fim != self.new.hora_fim
    
    def has_changes(self):
        return any([
            self.check_horario(),
            self.check_docentes(),
            self.check_salas(),
            self.check_dia(),
            self.check_turmas()
        ])

    def __str__(self):
        """Human-friendly string representation."""
        return (
                f"  Previous: {self.previous}\n"
                f"  New: {self.new})")
    