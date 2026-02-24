from datetime import datetime, timedelta
from typing import Any


def table_to_matrix(table: Any) -> list[list[Any]]:
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


def get_index(item: Any, matrix: list[list[Any]]) -> tuple[Any, list[list[Any]]]:
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
                    matrix[y][j] = None
                return j, matrix


def get_dia_from_index(index: int, spanMap: dict[str, Any]) -> str:
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


def are_weeks_overlapped(si1: str, sf1: str, si2: str, sf2: str) -> bool:
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
    early = min(date1_obj, date2_obj)
    return datetime.strftime(early, "%Y-%m-%d")


def max_date(date1: str, date2: str) -> str:
    """
    Recebe duas datas e devolve a que ocorre mais tarde.
    """
    date1_obj = datetime.strptime(date1, "%Y-%m-%d")
    date2_obj = datetime.strptime(date2, "%Y-%m-%d")
    late = max(date1_obj, date2_obj)
    return datetime.strftime(late, "%Y-%m-%d")
