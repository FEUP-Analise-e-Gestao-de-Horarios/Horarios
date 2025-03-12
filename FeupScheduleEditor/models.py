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
    def __init__(self, aula_id=None, cadeira_id=None, hora_inicio=None, duracao=None, dia=None, 
                 turmas_ids=None, docentes_ids=None, salas_ids=None):
        self.id = aula_id
        self.cadeira_id = cadeira_id
        self.hora_inicio = hora_inicio
        self.duracao = duracao
        self.dia = dia
        self.turmas_ids = turmas_ids
        self.docentes_ids = docentes_ids
        self.salas_ids = salas_ids

    def __str__(self):
        return f"AulaInfo(aula_id={self.id}, cadeira_id={self.cadeira_id}, hora_inicio={self.hora_inicio}, " \
               f"duracao={self.duracao}, dia={self.dia}, turmas_ids={self.turmas_ids}, " \
               f"docentes_ids={self.docentes_ids}, salas_ids={self.salas_ids})"

    @staticmethod
    def from_data(data):
        """Create an AulaInfo instance from the provided data."""
        
        # Extract all necessary values directly from the data
        aula_id = data['aulaId']
        cadeira_id = data['cadeiraId']
        hora_inicio = data['horaInicio']
        hora_fim = int(data['horaFim'])  # Ensure it's an integer for calculations
        turmas_ids = data['turmasIds']
        docentes_ids = [str(num) for num in data['docentesIds']]  # Convert to strings
        salas_ids = data['salasIds']
        
        # Calculate derived values
        duracao = utils.reverse_time_span_conversion(hora_fim - hora_inicio)  # Get the duration based on time difference
        dia = utils.switch_number_to_day(data['dia'])  # Convert day number to day name
        
        # Return a new AulaInfo object
        return AulaInfo(
            aula_id=aula_id,
            cadeira_id=cadeira_id,
            hora_inicio=hora_inicio,
            duracao=duracao,
            dia=dia,
            turmas_ids=turmas_ids,
            docentes_ids=docentes_ids,
            salas_ids=salas_ids
        )

class Change:
    def __init__(self, old, new):
        self.old_aula = old
        self.new_aula = new
        self.conflict = 0;
    def has_conflict(self):
        self.conflict = 1;