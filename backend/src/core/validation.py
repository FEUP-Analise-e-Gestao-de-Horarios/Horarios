from typing import get_origin

from django.http import JsonResponse, QueryDict
from pydantic import BaseModel, ValidationError

from src.core.errors import InvalidBodyResponse


def _format_validation_error(e: ValidationError) -> str:
    errors = e.errors(include_input=False, include_url=False)
    return "; ".join(
        f"{'.'.join(str(location) for location in err['loc'])}: {err['msg']}"
        if err.get("loc")
        else err["msg"]
        for err in errors
    )


def _query_params_to_dict(model: type[BaseModel], params: QueryDict) -> dict[str, object]:
    """Flatten a ``QueryDict`` honoring ``list[...]`` fields on ``model``.

    Repeated keys (``?x=a&x=b``) become a list when the matching field is
    declared as a list; otherwise the last value wins, matching Django's
    default ``QueryDict.dict()`` behavior.
    """
    list_fields = {
        name for name, field in model.model_fields.items() if get_origin(field.annotation) is list
    }
    return {key: params.getlist(key) if key in list_fields else params.get(key) for key in params}


def validate_request_body[M: BaseModel](
    model: type[M],
    body: bytes,
) -> tuple[M, None] | tuple[None, JsonResponse]:
    try:
        return model.model_validate_json(body), None
    except ValidationError as e:
        return None, InvalidBodyResponse(_format_validation_error(e))


def validate_query_params[M: BaseModel](
    model: type[M],
    params: QueryDict,
) -> tuple[M, None] | tuple[None, JsonResponse]:
    try:
        return model.model_validate(_query_params_to_dict(model, params)), None
    except ValidationError as e:
        return None, InvalidBodyResponse(_format_validation_error(e))
