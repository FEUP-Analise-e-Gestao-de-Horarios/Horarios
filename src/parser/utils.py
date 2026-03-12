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
