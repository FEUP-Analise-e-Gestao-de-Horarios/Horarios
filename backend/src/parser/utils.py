from django.http import JsonResponse
from pydantic import BaseModel, ValidationError

from src.core.errors import ApiError, error_response


def validate_request_body[M: BaseModel](
    model: type[M],
    body: bytes,
) -> tuple[M, None] | tuple[None, JsonResponse]:
    try:
        return model.model_validate_json(body), None
    except ValidationError as e:
        errors = e.errors(include_input=False, include_url=False)
        message = "; ".join(
            f"{'.'.join(str(l) for l in err['loc'])}: {err['msg']}"
            if err.get("loc")
            else err["msg"]
            for err in errors
        )
        return None, error_response(status=400, code=ApiError.INVALID_BODY, message=message)
