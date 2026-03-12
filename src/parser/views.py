import logging
import os
import sqlite3
from collections import defaultdict

from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt

from src.projects.models import Project

from .models import AulasSimultaneasInput
from .parallel import check_parallel_classes, get_parallel_classes
from .utils import validate_request_body

logger = logging.getLogger(__name__)


def selecionar_aulas_em_paralelo(request: HttpRequest):
    if not request.user.is_authenticated:
        return redirect("signin")

    project_id_raw = request.GET.get("id")
    if project_id_raw is None:
        return JsonResponse({"error": "Invalid project ID"}, status=400)
    try:
        project_id = int(project_id_raw)
    except ValueError:
        return JsonResponse({"error": "Invalid project ID"}, status=400)

    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse({"error": "Project not found"}, status=404)

    person = request.user
    user_groups = set(person.core_groups.values_list("id", flat=True))
    project_groups = set(project.group.values_list("id", flat=True))

    if not (
        project.creator == person
        or request.user.is_staff
        or project.people.filter(pk=person.pk).exists()
        or bool(user_groups & project_groups)
    ):
        return JsonResponse({"error": "Forbidden"}, status=403)

    db_path = os.path.join(
        settings.BASE_DIR,
        "database",
        f"Project{project_id}",
        "initial_database.db",
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

    cursos_unicos = {grupo["curso"] for grupo in grupos_list}
    grupos_list.sort(key=lambda g: (g["curso"], g["nomeUC"]))

    general_db_path = os.path.join(
        settings.BASE_DIR,
        "database",
        f"Project{project_id}",
        "general_database.db",
    )
    general_conn = sqlite3.connect(general_db_path)
    general_conn.row_factory = sqlite3.Row
    general_cursor = general_conn.cursor()
    aulas_em_paralelo = get_parallel_classes(general_cursor)
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
def guardar_aulas_em_paralelo(request: HttpRequest) -> JsonResponse:
    if not request.user.is_authenticated:
        return JsonResponse({"error": "User is not authenticated"}, status=401)

    project_id_raw = request.GET.get("id")
    if project_id_raw is None:
        return JsonResponse({"error": "Invalid project ID"}, status=400)
    try:
        project_id = int(project_id_raw)
    except ValueError:
        return JsonResponse({"error": "Invalid project ID"}, status=400)

    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        return JsonResponse({"error": "Project not found"}, status=404)

    person = request.user
    user_groups = set(person.core_groups.values_list("id", flat=True))
    project_groups = set(project.group.values_list("id", flat=True))

    if not (
        project.creator == person
        or request.user.is_staff
        or project.people.filter(pk=person.pk).exists()
        or bool(user_groups & project_groups)
    ):
        return JsonResponse({"error": "Forbidden"}, status=403)

    try:
        validated, err = validate_request_body(AulasSimultaneasInput, request.body)
        if err:
            return err
        assert validated is not None

        db_path = os.path.join(
            settings.BASE_DIR,
            "database",
            f"Project{project_id}",
            "general_database.db",
        )

        with sqlite3.connect(db_path, timeout=10) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("DELETE FROM turmasSimultaneas")
            for par in validated.pares:
                cursor.execute(
                    """
                    INSERT INTO turmasSimultaneas (aula1, aula2, turma1, turma2)
                    VALUES (?, ?, ?, ?)
                    """,
                    (par.aula1, par.aula2, par.turma1, par.turma2),
                )
            conn.commit()

            inconsistentes = check_parallel_classes(cursor, validated.pares)

            project.has_selected_aulas_em_paralelo = True
            project.save()

            return JsonResponse({"status": "ok", "inconsistentes": inconsistentes})

    except Exception as e:
        return JsonResponse({"status": "erro", "message": str(e)}, status=500)
