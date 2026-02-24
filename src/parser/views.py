import concurrent.futures
import json
import os
import sqlite3
import threading
import traceback
from collections import defaultdict

import bleach
from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from pydantic import ValidationError

from core.models import Project

from .models import AulasSimultaneasInput
from .parallel import obter_aulas_em_paralelo, verificar_aulas_em_paralelo
from .scraper import Parser

max_workers = 4  # Estabelece o número máximo de threads permitidas
executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
_parse_counter = {"count": 0}
_parse_counter_lock = threading.Lock()


def parse(request: HttpRequest) -> JsonResponse:
    """
    Inicia o parse de um novo projeto.

    Prepara as variáveis e realiza as verificações necessárias para realizar
    o parse da página de horários. Cria um objeto Parser e submete-o a uma
    nova thread, enquanto houver threads disponíveis.
    """

    if not request.user.is_authenticated:
        return JsonResponse({"error": "User is not authenticated"}, status=401)

    if request.method != "POST":
        return JsonResponse({"error": "Invalid request"}, status=400)

    with _parse_counter_lock:
        if _parse_counter["count"] >= 5:
            return JsonResponse(
                {
                    "error": "Número máximo de parses simultâneos excedidos. Por favor espere um pouco antes de tentar novamente."
                },
                status=423,
            )
        _parse_counter["count"] += 1

    paginas = bleach.clean(request.POST.get("paginas"))
    name = bleach.clean(request.POST.get("name"))
    parser = Parser(paginas=paginas, user_pk=request.user.pk, name=name)

    def run():
        try:
            parser.run()
        except Exception:
            print(traceback.format_exc())
        finally:
            with _parse_counter_lock:
                _parse_counter["count"] -= 1

    try:
        executor.submit(run)
        return JsonResponse({}, status=200)
    except Exception:
        with _parse_counter_lock:
            _parse_counter["count"] -= 1
        return JsonResponse(
            {"error": "Nao foi possivel fazer parse do site"}, status=400
        )


def selecionar_aulas_em_paralelo(request: HttpRequest):
    project_id = request.GET.get("id")

    db_path = os.path.join(
        settings.BASE_DIR, "database", f"Project{project_id}", "initial_database.db"
    )
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            a.id AS aula_id,
            at.idTurma AS turma_id,
            a.diaSemana,
            a.horaInicial,
            a.semanaInicial,
            auc.idUC,
            uc.idCurso,
            uc.nome AS nomeUC
        FROM aula a
        JOIN aulaTurmas at ON a.id = at.idAula
        JOIN aulaUC auc ON a.id = auc.idAula
        JOIN uc ON auc.idUC = uc.codigo
        WHERE a.teorico = FALSE
    """)

    resultados_query = cursor.fetchall()

    # Agrupar numa lista aulas da mesma UC (e curso) que são ao mesmo tempo
    grupos_dict = defaultdict(list)
    for row in resultados_query:
        key = (
            row["diaSemana"],
            row["horaInicial"],
            row["semanaInicial"],
            row["idUC"],
            row["nomeUC"],
            row["idCurso"],
        )
        turmas_por_aula = grupos_dict.setdefault(key, defaultdict(set))
        turmas_por_aula[row["aula_id"]].add(row["turma_id"])

    grupos_list = []
    for i, (key, aulas) in enumerate(grupos_dict.items(), start=1):
        if len(aulas) <= 1:
            continue

        dia_semana, hora_inicial, _semana_inicial, codigoUC, nomeUC, id_curso = key
        hora_str = f"{hora_inicial:04d}"
        hora_str = f"{hora_str[:2]}:{hora_str[2:]}"
        horario_str = f"{dia_semana}, {hora_str}"

        num_boxes = len(aulas) // 2

        grupo_dict = {
            "id": i,
            "uc": codigoUC,
            "nomeUC": nomeUC,
            "curso": id_curso,
            "horario": horario_str,
            "aulas": sorted(
                [
                    (aula_id, sorted([turma.strip() for turma in turmas]))
                    for aula_id, turmas in aulas.items()
                ],
                key=lambda x: x[1][0],
            ),
            "num_boxes": num_boxes,
        }

        grupos_list.append(grupo_dict)

    cursos_unicos = sorted(grupo["curso"] for grupo in grupos_list)
    grupos_list.sort(key=lambda g: (g["curso"], g["nomeUC"]))

    general_db_path = os.path.join(
        settings.BASE_DIR, "database", f"Project{project_id}", "general_database.db"
    )
    general_conn = sqlite3.connect(general_db_path)
    general_conn.row_factory = sqlite3.Row
    general_cursor = general_conn.cursor()
    aulas_em_paralelo = obter_aulas_em_paralelo(general_cursor)
    general_conn.close()

    conn.close()

    return render(
        request,
        "selecionar_aulas_em_paralelo.html",
        {
            "grupos_aulas_ao_mesmo_tempo": grupos_list,
            "cursos": cursos_unicos,
            "project_id": project_id,
            "aulas_em_paralelo": aulas_em_paralelo,
        },
    )


@csrf_exempt
def guardar_aulas_em_paralelo(request: HttpRequest):
    try:
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse(
                {"status": "erro", "message": "Invalid JSON body"}, status=400
            )
        if not isinstance(data, dict):
            return JsonResponse(
                {"status": "erro", "message": "Request body must be a JSON object"},
                status=400,
            )
        try:
            validated = AulasSimultaneasInput(pares=data.get("pares", []))
        except ValidationError as e:
            return JsonResponse({"status": "erro", "message": e.errors()}, status=400)
        pares = [(p.aula1, p.aula2, p.turma1, p.turma2) for p in validated.pares]

        if len(pares) == 0:
            return JsonResponse({"status": "ignorado"})

        project_id = request.GET.get("id")
        db_path = os.path.join(
            settings.BASE_DIR, "database", f"Project{project_id}", "general_database.db"
        )

        with sqlite3.connect(db_path, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("DELETE FROM turmasSimultaneas")
            for a1, a2, t1, t2 in pares:
                cursor.execute(
                    """
                    INSERT INTO turmasSimultaneas (aula1, aula2, turma1, turma2)
                    VALUES (?, ?, ?, ?)
                """,
                    (a1, a2, t1, t2),
                )
            conn.commit()

            inconsistentes = verificar_aulas_em_paralelo(cursor, pares)

            project = Project.objects.get(id=project_id)
            project.has_selected_aulas_em_paralelo = True
            project.save()

            return JsonResponse({"status": "ok", "inconsistentes": inconsistentes})

    except Exception as e:
        return JsonResponse({"status": "erro", "message": str(e)}, status=500)
