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
