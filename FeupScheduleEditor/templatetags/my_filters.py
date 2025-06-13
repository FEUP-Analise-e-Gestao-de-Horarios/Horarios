from django import template

register = template.Library()

@register.filter(name='sort')
def sort(value):
    if isinstance(value, list):
        return sorted(value)
    return value

@register.filter(name='times') 
def times(start, end):
    return range(start, end+1)

@register.filter(name='firstHalfHour')
def firstHalfHour(num):
    num_str = str(num)
    return f"{num_str}:00"

@register.filter(name='secondHalfHour')
def secondHalfHour(num):
    num_str = str(num)
    return f"{num_str}:30"

@register.filter(name='add')
def add(value, arg):
    return int(value) + int(arg)

@register.filter(name='multiply')
def multiply(num1, num2):
    return int(num1) * int(num2)

@register.filter(name='concat')
def concat(value1, value2):
    return str(value1) + str(value2)

@register.filter(name='getDay')
def getDay(num_turmas, num):
    num = num / num_turmas
    if 0 <=num <= 1:
        return "segunda"
    elif 1 < num <= 2:
        return "terça"
    elif 2 < num <= 3:
        return "quarta"
    elif 3 < num <= 4:
        return "quinta"
    elif 4 < num <= 5:
        return "sexta"
    elif 5 < num <= 6:
        return "sábado"

@register.filter(name='getTurma')    
def getTurma(num_turmas, num):
    num = num % num_turmas
    if num == 0:
        num = num_turmas
    return num

@register.filter(name='turnoRange')
def turnoRange(dic, turno_num):
    if turno_num == 1:
        return range(1, dic[turno_num]+1)
    else:
        return range(dic[turno_num-1] +1, dic[turno_num-1]+ dic[turno_num]+1)
    
@register.filter(name='generateDic')
def generateDic(dic):
    dic = {1: 5, 2: 10}
    return dic

@register.filter(name='getSize')
def getSize(dic):
    return len(dic)

@register.filter(name='getTurno')
def getTurno(dic, turma_nome):
    for turno, turmas in dic.items():
        if turma_nome in turmas:
            return turno
        
@register.filter(name='getTurnosForTurma')
def getTurnosForTurma(dic, turma_nome):
    turnos = []
    for turno, turmas in dic.items():
        if turma_nome in turmas:
            turnos.append(turno)
    return turnos

@register.filter(name='getAllTurmas')
def getAllTurmas(dic):
    turmasSet = set()
    for _, turmas in dic.items():
        for turma in turmas:
            turmasSet.add(turma)
    return list(turmasSet)
        
@register.filter(name='getTurmaName')
def getTurmaName(lista, numTurma):
    return lista[numTurma-1]

@register.filter(name='getTurmasTurno')
def getTurmasTurno(dictionary, numTurno):
    if(0 in dictionary):
        return dictionary[numTurno - 1]
    return dictionary[numTurno]

@register.filter
def is_number(value):
    try:
        int(value)
        return True
    except ValueError:
        return False
    
@register.simple_tag(name="is_busy")
def is_busy(aulas, dia, hora):
    # Convert the input hour to an integer for easier comparison
    horaInicioInput = int(hora.replace(":", ""))
    
    for aula in aulas:
        if aula.diaSemana == dia:
            duracaoEmMinutos = aula.duracao * 30
            horaFimAula = aula.horaInicial + duracaoEmMinutos
            fatorAjuste = 0
            if aula.duracao > 1:
                fatorAjuste = aula.duracao // 2
            horaFimAula += fatorAjuste * 40

            if horaInicioInput >= aula.horaInicial and horaInicioInput < horaFimAula:
                return True
    return False
    
@register.simple_tag(takes_context=True)
def init_busy_counter(context):
    context['busy_counter'] = 0
    return ''

@register.simple_tag(takes_context=True)
def increment_if_busy(context, is_busy):
    if is_busy:
        context['busy_counter'] += 1
    return 'busy' if is_busy else ''

@register.simple_tag(takes_context=True, name="can_mark_busy")
def can_mark_busy(context, aulas):
    return context.get('busy_counter', 0) < len(aulas)

@register.filter(name='dict_get')
def dict_get(d, key):
    return d.get(key)

@register.filter(name='get_day_name')
def get_day_name(num):
    days = ["Segunda", "Terça", "Quarta", "Quinta", "Sexta", "Sábado"]
    return days[num] if num < len(days) else ""

@register.filter
def extract_sigla(value):
    if value is None:
        return ""
    return str(value).split('(')[0].strip()

@register.filter(name='get_overlapping_aulas')
def get_overlapping_aulas(aulas, current_aula):
    if not aulas or not current_aula:
        return []
    
    def hora_to_minutes(hora):
        """Converts 'HHMM' string to total minutes (e.g., '1700' → 1020)."""
        hora_str = str(hora).zfill(4)  # Ensure 4 digits (e.g., '900' → '0900')
        h = int(hora_str[:2])  # Hours
        m = int(hora_str[2:])  # Minutes
        return h * 60 + m

    current_start = hora_to_minutes(current_aula['horaInicial'])
    current_duration = current_aula['duracao'] * 30  # Convert to minutes (30 min per unit)
    current_end = current_start + current_duration
    
    overlapping = []
    for aula in aulas:
        if aula['diaSemana'] != current_aula['diaSemana']:
            continue  # Skip if different day
        
        aula_start = hora_to_minutes(aula['horaInicial'])
        aula_duration = aula['duracao'] * 30
        aula_end = aula_start + aula_duration
        
        # Check if classes overlap (even partially)
        if (aula_start < current_end and aula_end > current_start):
            # Only include if it's the same UC or different sections
            overlapping.append(aula)
    
    return overlapping

@register.filter
def split(value, key):
    """Returns the value turned into a list split by the given key."""
    if not value:
        return []
    return value.split(key)

