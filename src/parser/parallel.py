import sqlite3
from collections import defaultdict, deque
from typing import TypedDict

from parser.models import ParAulasSimultaneas


class GrupoInconsistente(TypedDict):
    nome_uc: str
    aulas: list[str]


Lesson = int


def get_parallel_classes(cursor: sqlite3.Cursor) -> list[list[int]]:
    """
    Returns the lessons that are currently stored as parallel lessons,
    in the form of a list of parallel lesson groups (lists of lesson IDs).
    """

    cursor.execute("SELECT aula1, aula2 FROM turmasSimultaneas")
    pares = cursor.fetchall()

    # Build graph lesson -> neighbors
    adj: defaultdict[Lesson, set[Lesson]] = defaultdict(set)
    for lessonA, lessonB in pares:
        adj[lessonA].add(lessonB)
        adj[lessonB].add(lessonA)

    # Get chains (connected components via BFS)
    visited: set[Lesson] = set()
    chains: list[list[Lesson]] = []

    for lesson in adj:
        if lesson in visited:
            continue

        queue = deque([lesson])
        chain: list[Lesson] = []

        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            chain.append(current)
            queue.extend(adj[current] - visited)

        chain.sort()
        chains.append(chain)

    return chains


def check_parallel_classes(
    cursor: sqlite3.Cursor,
    pares: list[ParAulasSimultaneas],
) -> list[GrupoInconsistente]:
    """
    Checks which groups from the parallel class selection have changed
    and are not, at the moment, being taught at the same time due to swaps.

    Intended for cases where the user changes the groups after swaps have already been made.
    """

    # Build graph lesson -> neighbors
    adj: defaultdict[Lesson, set[Lesson]] = defaultdict(set)
    for par in pares:
        adj[par.aula1].add(par.aula2)
        adj[par.aula2].add(par.aula1)

    # Get groups of simultaneous lessons as chains
    visited_lessons: set[int] = set()
    chain_of_lessons: list[list[Lesson]] = []

    for lesson in adj:
        if lesson in visited_lessons:
            continue

        queue = deque([lesson])
        chain: list[Lesson] = []

        while queue:
            current = queue.popleft()
            if current in visited_lessons:
                continue
            visited_lessons.add(current)
            chain.append(current)
            queue.extend(adj[current] - visited_lessons)

        chain.sort()
        chain_of_lessons.append(chain)

    # Check for each chain whether the lessons have the same day, time, and week range
    inconsistent: list[list[Lesson]] = []

    for chain in chain_of_lessons:
        cursor.execute(
            f"""
            SELECT id, diaSemana, horaInicial, semanaInicial, semanaFinal
            FROM aula
            WHERE id IN ({",".join(["?"] * len(chain))})
            """,
            chain,
        )
        aulas_info = cursor.fetchall()

        if not aulas_info or len(aulas_info) != len(chain):
            inconsistent.append(chain)
            continue

        reference = (
            aulas_info[0]["diaSemana"],
            aulas_info[0]["horaInicial"],
            aulas_info[0]["semanaInicial"],
            aulas_info[0]["semanaFinal"],
        )

        for lesson in aulas_info[1:]:
            current = (
                lesson["diaSemana"],
                lesson["horaInicial"],
                lesson["semanaInicial"],
                lesson["semanaFinal"],
            )
            if current != reference:
                inconsistent.append(chain)
                break  # This lesson is already marked as inconsistent

    if not inconsistent:
        return []

    grupos_inconsistentes: list[GrupoInconsistente] = []

    for chain in inconsistent:
        cursor.execute(
            f"""
            SELECT a.id, uc.nome as nomeUC, group_concat(t.codigo, ', ') as turmas
            FROM aula a
            JOIN aulaUC auc ON a.id = auc.idAula
            JOIN uc ON auc.idUC = uc.codigo
            JOIN aulaTurmas at ON a.id = at.idAula
            JOIN turmas t ON at.idTurma = t.codigo
            WHERE a.id IN ({",".join(["?"] * len(chain))})
            GROUP BY a.id
            """,
            chain,
        )
        aulas = cursor.fetchall()
        if aulas:
            nome_uc: str = aulas[0]["nomeUC"]
            lista: GrupoInconsistente = {
                "nome_uc": nome_uc,
                "aulas": [f"Lesson with groups: {a['turmas']}" for a in aulas],
            }
            grupos_inconsistentes.append(lista)

    return grupos_inconsistentes
