import sqlite3
from collections import defaultdict, deque
from typing import Any


def obter_aulas_em_paralelo(cursor: sqlite3.Cursor) -> list[Any]:
    """
    Devolve as aulas que atualmente estão guardadas como aulas em paralelo,
    em forma de uma lista dos grupos de aulas em paralelo (listas de IDs de aulas).
    """

    cursor.execute("SELECT aula1, aula2 FROM turmasSimultaneas")
    pares = cursor.fetchall()

    # Construir grafo aula -> vizinhos
    adj = defaultdict(set)
    for a1, a2 in pares:
        adj[a1].add(a2)
        adj[a2].add(a1)

    # Obter cadeias (componentes conexas via BFS)
    visitados = set()
    cadeias = []

    for aula in adj:
        if aula in visitados:
            continue

        fila = deque([aula])
        cadeia = []

        while fila:
            atual = fila.popleft()
            if atual in visitados:
                continue
            visitados.add(atual)
            cadeia.append(atual)
            fila.extend(adj[atual] - visitados)

        cadeia.sort()
        cadeias.append(cadeia)

    return cadeias


def verificar_aulas_em_paralelo(cursor: sqlite3.Cursor, pares: list) -> list:
    """
    Verifica quais dos grupos da seleção de aulas em paralelo sofreram mudanças
    e não estão, de momento, a ser dadas ao mesmo tempo devido às trocas.

    Destinada para casos em que o utilizador muda os grupos depois de já terem
    sido realizadas trocas.
    """

    # Construir grafo aula -> vizinhos
    adj = defaultdict(set)
    for a1, a2, _, _ in pares:
        adj[a1].add(a2)
        adj[a2].add(a1)

    # Obter grupos de aulas simultâneas em forma de cadeia
    visitados = set()
    cadeias = []

    for aula in adj:
        if aula in visitados:
            continue

        fila = deque([aula])
        cadeia = []

        while fila:
            atual = fila.popleft()
            if atual in visitados:
                continue
            visitados.add(atual)
            cadeia.append(atual)
            fila.extend(adj[atual] - visitados)

        cadeia.sort()
        cadeias.append(cadeia)

    # Verificar para cada cadeia se as aulas têm o mesmo dia, hora e intervalo de semanas
    inconsistentes = []

    for cadeia in cadeias:
        cursor.execute(
            f"""
            SELECT id, diaSemana, horaInicial, semanaInicial, semanaFinal
            FROM aula
            WHERE id IN ({",".join(["?"] * len(cadeia))})
            """,
            cadeia,
        )
        aulas_info = cursor.fetchall()

        if not aulas_info:
            continue

        referencia = (
            aulas_info[0]["diaSemana"],
            aulas_info[0]["horaInicial"],
            aulas_info[0]["semanaInicial"],
            aulas_info[0]["semanaFinal"],
        )

        for aula in aulas_info[1:]:
            atual = (
                aula["diaSemana"],
                aula["horaInicial"],
                aula["semanaInicial"],
                aula["semanaFinal"],
            )
            if atual != referencia:
                inconsistentes.append(cadeia)
                break  # esta cadeia já está marcada como inconsistente

    if inconsistentes:
        grupos_inconsistentes = []

        for cadeia in inconsistentes:
            cursor.execute(
                f"""
                SELECT a.id, uc.nome as nomeUC, group_concat(t.codigo, ', ') as turmas
                FROM aula a
                JOIN aulaUC auc ON a.id = auc.idAula
                JOIN uc ON auc.idUC = uc.codigo
                JOIN aulaTurmas at ON a.id = at.idAula
                JOIN turmas t ON at.idTurma = t.codigo
                WHERE a.id IN ({",".join(["?"] * len(cadeia))})
                GROUP BY a.id
                """,
                cadeia,
            )
            aulas = cursor.fetchall()
            if aulas:
                nome_uc = aulas[0]["nomeUC"]
                lista = {
                    "nome_uc": nome_uc,
                    "aulas": [f"Aula com as turmas: {a['turmas']}" for a in aulas],
                }
                grupos_inconsistentes.append(lista)

        return grupos_inconsistentes

    return []
