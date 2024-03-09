lista = [['2LEIC09', '2LEIC10', '2LEIC11', '2LEIC12', '2LEIC13', '2LEIC14', '2LEIC15', '2LEIC16', '2LEIC17'], ['2LEIC01', '2LEIC02', '2LEIC03', '2LEIC04', '2LEIC05', '2LEIC06', '2LEIC07', '2LEIC08']]

print(sorted(lista, key=lambda x: int(x[0][-2:])))