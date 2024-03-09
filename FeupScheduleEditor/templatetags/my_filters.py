from django import template

register = template.Library()

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
        
@register.filter(name='getTurmaName')
def getTurmaName(lista, numTurma):
    return lista[numTurma-1]

@register.filter(name='getTurmasTurno')
def getTurmasTurno(dictionary, numTurno):
    if(0 in dictionary):
        return dictionary[numTurno - 1]
    return dictionary[numTurno]