from datetime import datetime, timedelta
from typing import Any

from django.http import JsonResponse
from pydantic import BaseModel, ValidationError


def validate_request_body[M: BaseModel](
    model: type[M],
    body: bytes,
) -> tuple[M, None] | tuple[None, JsonResponse]:
    try:
        return model.model_validate_json(body), None
    except ValidationError as e:
        return None, JsonResponse(
            {
                "status": "erro",
                "message": e.errors(include_input=False, include_url=False),
            },
            status=400,
        )


def get_dia_from_index(index: int, spanMap: dict[str, Any]) -> str:
    """
    Recebe um índice e um mapa de spans HTML, devolvendo o dia da semana.
    """

    if index == 1:
        return "Segunda"
    count = 0
    for dia, span in spanMap.items():
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
